"""Security-only targeted feedback. Identities never exposed; tallies only."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from .. import wifi
from ..auth import Principal, require_security
from ..db import get_conn, now_iso
from ..events import publish
from ..models import FeedbackCreate, FeedbackCreated, FeedbackResults

router = APIRouter(prefix="/api", tags=["feedback"])


@router.post("/feedback", response_model=FeedbackCreated)
def create_feedback(body: FeedbackCreate, principal: Principal = Depends(require_security)):
    with get_conn() as conn:
        zone = conn.execute(
            "SELECT id FROM zone WHERE building_id=? AND "
            "((floor IS NULL AND ? IS NULL) OR floor=?)",
            (body.building_id, body.floor, body.floor),
        ).fetchone()
        created = now_iso()
        cur = conn.execute(
            "INSERT INTO feedback_request(zone_id, building_id, floor, question, "
            "created_by, created_at) VALUES (?,?,?,?,?,?)",
            (zone["id"] if zone else None, body.building_id, body.floor,
             body.question, principal.user_id, created),
        )
        fid = cur.lastrowid
    eligible = wifi.eligible_count(body.building_id, body.floor)
    publish("feedback.created", {"request_id": fid, "building_id": body.building_id,
                                 "floor": body.floor})
    return FeedbackCreated(id=fid, eligible_device_count=eligible)


@router.get("/feedback/{request_id}/results", response_model=FeedbackResults)
def feedback_results(request_id: int, _: Principal = Depends(require_security)):
    with get_conn() as conn:
        req = conn.execute(
            "SELECT question FROM feedback_request WHERE id=?", (request_id,)
        ).fetchone()
        if req is None:
            raise HTTPException(404, "Feedback request not found")
        rows = conn.execute(
            "SELECT answer, COUNT(*) AS n FROM feedback_response "
            "WHERE request_id=? GROUP BY answer",
            (request_id,),
        ).fetchall()
    tallies = {"yes": 0, "no": 0, "unsure": 0}
    for r in rows:
        tallies[r["answer"]] = r["n"]
    return FeedbackResults(id=request_id, question=req["question"], tallies=tallies,
                           total=sum(tallies.values()))
