"""Student-facing endpoints. Students never see other students' reports or identities."""
from __future__ import annotations

import uuid
from pathlib import Path

import time

from fastapi import (APIRouter, BackgroundTasks, Depends, File, Form, HTTPException,
                     Request, UploadFile)
from fastapi.responses import StreamingResponse

from .. import config, wifi
from ..auth import Principal, get_principal, require_student
from ..db import get_conn
from ..events import event_stream, subscribe
from ..models import (FeedbackAnswer, ReportAck, StudentAlert, StudentFeedbackItem,
                      WifiSuggestion)
from ..service_reports import create_report, run_analysis

router = APIRouter(prefix="/api", tags=["student"])

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_IMAGE_BYTES = 6 * 1024 * 1024


@router.get("/wifi/suggest", response_model=WifiSuggestion)
def wifi_suggest(principal: Principal = Depends(require_student)) -> WifiSuggestion:
    return WifiSuggestion(**wifi.suggest_for_device(principal.device_id))


@router.post("/reports", response_model=ReportAck)
async def submit_report(
    background: BackgroundTasks,
    observation_type: str = Form(...),
    building_id: int = Form(...),
    floor: int | None = Form(default=None),
    description: str | None = Form(default=None),
    photo: UploadFile | None = File(default=None),
    principal: Principal = Depends(require_student),
) -> ReportAck:
    if observation_type not in ("saw", "heard", "was_told"):
        raise HTTPException(422, "Invalid observation_type")
    if description and len(description) > 2000:
        description = description[:2000]

    photo_path = None
    if photo is not None:
        # Treat upload as untrusted: validate type/size, store with a random name,
        # never derived from client-provided filename.
        if photo.content_type not in ALLOWED_IMAGE_TYPES:
            raise HTTPException(415, "Unsupported image type")
        data = await photo.read()
        if len(data) > MAX_IMAGE_BYTES:
            raise HTTPException(413, "Image too large")
        config.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        ext = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}[
            photo.content_type]
        fname = f"{uuid.uuid4().hex}{ext}"
        (config.UPLOAD_DIR / fname).write_bytes(data)
        photo_path = str(Path("uploads") / fname)

    result = create_report(
        reporter_user_id=principal.user_id,
        device_id=principal.device_id,
        observation_type=observation_type,
        building_id=building_id,
        floor=floor,
        description=description,
        photo_path=photo_path,
    )
    # Analysis runs asynchronously — submission is acknowledged immediately.
    background.add_task(run_analysis, result["id"])
    return ReportAck(id=result["id"], created_at=result["created_at"])


@router.get("/feedback/mine", response_model=list[StudentFeedbackItem])
def my_feedback(principal: Principal = Depends(require_student)):
    suggestion = wifi.suggest_for_device(principal.device_id)
    building_id = suggestion.get("building_id")
    floor = suggestion.get("floor")
    if building_id is None:
        return []
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT fr.id AS id, fr.question AS question, b.name AS building_name, "
            "fr.floor AS floor FROM feedback_request fr "
            "LEFT JOIN building b ON b.id = fr.building_id "
            "WHERE fr.building_id = ? AND (fr.floor IS NULL OR fr.floor = ?)",
            (building_id, floor),
        ).fetchall()
    return [StudentFeedbackItem(id=r["id"], question=r["question"],
                                building_name=r["building_name"], floor=r["floor"])
            for r in rows]


@router.post("/feedback/{request_id}/respond")
def respond_feedback(request_id: int, body: FeedbackAnswer,
                     principal: Principal = Depends(require_student)):
    from ..db import now_iso
    with get_conn() as conn:
        exists = conn.execute(
            "SELECT 1 FROM feedback_request WHERE id=?", (request_id,)
        ).fetchone()
        if not exists:
            raise HTTPException(404, "Feedback request not found")
        conn.execute(
            "INSERT INTO feedback_response(request_id, device_id, answer, created_at) "
            "VALUES (?,?,?,?)",
            (request_id, principal.device_id, body.answer, now_iso()),
        )
    from ..events import publish
    publish("feedback.response", {"request_id": request_id})
    return {"status": "recorded"}


@router.get("/alerts/mine", response_model=list[StudentAlert])
def my_alerts(principal: Principal = Depends(require_student)):
    suggestion = wifi.suggest_for_device(principal.device_id)
    building_id = suggestion.get("building_id")
    floor = suggestion.get("floor")
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT a.id AS id, a.scope AS scope, b.name AS building_name, "
            "a.floor AS floor, a.message AS message, a.approved_at AS approved_at, "
            "u.display_name AS source FROM alert a "
            "LEFT JOIN building b ON b.id = a.building_id "
            "LEFT JOIN app_user u ON u.id = a.approved_by "
            "ORDER BY a.approved_at DESC",
        ).fetchall()
    out = []
    for r in rows:
        if r["scope"] == "campus":
            relevant = True
        elif r["scope"] == "building":
            relevant = building_id is not None and _building_matches(r, building_id)
        else:  # floor
            relevant = (building_id is not None and _building_matches(r, building_id)
                        and r["floor"] == floor)
        if relevant:
            out.append(StudentAlert(
                id=r["id"], scope=r["scope"], building_name=r["building_name"],
                floor=r["floor"], message=r["message"],
                source=f"Campus Security · {r['source']}", issued_at=r["approved_at"]))
    return out


def _building_matches(row, building_id: int) -> bool:
    with get_conn() as conn:
        b = conn.execute(
            "SELECT id FROM building WHERE name=?", (row["building_name"],)
        ).fetchone()
    return b is not None and b["id"] == building_id


class _ZoneAudience:
    """Audience predicate for a student's live event stream.

    Forwards only zone-targeted pushes (feedback requests and alerts) that match the
    student's current simulated Wi-Fi zone, plus campus-wide alerts. The student's zone
    is resolved from backend-only Wi-Fi data and refreshed periodically so a device that
    moves into the zone starts receiving pushes. The predicate never puts any identity
    into the outgoing payload — it only gates delivery.
    """

    PUSH_TYPES = {"feedback.created", "alert.created"}
    REFRESH_SEC = 10

    def __init__(self, device_id: str | None):
        self.device_id = device_id
        self._building_id: int | None = None
        self._floor: int | None = None
        self._refreshed_at = 0.0
        self._refresh()

    def _refresh(self) -> None:
        s = wifi.suggest_for_device(self.device_id)
        self._building_id = s.get("building_id")
        self._floor = s.get("floor")
        self._refreshed_at = time.monotonic()

    def __call__(self, event_type: str, data: dict) -> bool:
        if event_type not in self.PUSH_TYPES:
            return False
        if time.monotonic() - self._refreshed_at > self.REFRESH_SEC:
            self._refresh()

        scope = data.get("scope")
        # Campus-wide alerts reach everyone.
        if event_type == "alert.created" and scope == "campus":
            return True
        if self._building_id is None:
            return False
        if data.get("building_id") != self._building_id:
            return False
        # Floor-scoped push only matches when the student is on that floor.
        target_floor = data.get("floor")
        if target_floor is not None and target_floor != self._floor:
            return False
        return True


@router.get("/student/events")
async def student_events(request: Request, authorization: str | None = None):
    """Live push stream for a student. EventSource cannot send headers, so the token is
    accepted as a query param; the student role is validated before streaming. Delivery
    is gated by the student's current zone via a server-side audience predicate.
    """
    token = request.query_params.get("token")
    auth_header = f"Bearer {token}" if token else authorization
    principal = get_principal(auth_header)
    if principal.role != "student":
        raise HTTPException(403, "Student role required")

    sub = subscribe(audience=_ZoneAudience(principal.device_id),
                    meta={"kind": "student"})

    async def gen():
        async for chunk in event_stream(sub):
            if await request.is_disconnected():
                break
            yield chunk

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache",
                                      "X-Accel-Buffering": "no"})
