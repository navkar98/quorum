"""Security-only alert management. Backend-enforced authorization + audit record."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from .. import wifi
from ..auth import Principal, require_security
from ..db import get_conn, now_iso
from ..events import publish
from ..models import AlertCreate, AlertOut, AlertPreview, AlertPreviewOut

router = APIRouter(prefix="/api", tags=["alerts"])


def _audience_count(scope: str, building_id: int | None, floor: int | None) -> int:
    if scope == "campus":
        return wifi.eligible_count(None, None, campus=True)
    if scope == "building":
        return wifi.eligible_count(building_id, None)
    return wifi.eligible_count(building_id, floor)


@router.post("/alerts/preview", response_model=AlertPreviewOut)
def preview_alert(body: AlertPreview, _: Principal = Depends(require_security)):
    return AlertPreviewOut(
        audience_device_count=_audience_count(body.scope, body.building_id, body.floor))


@router.post("/alerts", response_model=AlertOut)
def approve_alert(body: AlertCreate, principal: Principal = Depends(require_security)):
    """Approve+send a simulated alert. Requires authenticated security identity and
    writes an auditable approval record. No AI/report/flag can reach this path.
    """
    if body.scope in ("building", "floor") and body.building_id is None:
        raise HTTPException(422, "building_id required for building/floor scope")
    if body.scope == "floor" and body.floor is None:
        raise HTTPException(422, "floor required for floor scope")

    approved = now_iso()
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO alert(scope, building_id, floor, message, approved_by, "
            "approved_at) VALUES (?,?,?,?,?,?)",
            (body.scope, body.building_id, body.floor, body.message,
             principal.user_id, approved),
        )
        alert_id = cur.lastrowid
        # Auditable approval record (who, when, audience, content).
        audience = _audience_count(body.scope, body.building_id, body.floor)
        conn.execute(
            "INSERT INTO alert_audit(alert_id, actor_id, action, detail, at) "
            "VALUES (?,?,?,?,?)",
            (alert_id, principal.user_id, "approve",
             f"scope={body.scope} building={body.building_id} floor={body.floor} "
             f"audience={audience} msg_len={len(body.message)}", approved),
        )
        name_row = conn.execute(
            "SELECT name FROM building WHERE id=?", (body.building_id,)
        ).fetchone() if body.building_id else None

    publish("alert.created", {"alert_id": alert_id, "scope": body.scope,
                              "building_id": body.building_id, "floor": body.floor})
    return AlertOut(
        id=alert_id, scope=body.scope, building_id=body.building_id,
        building_name=name_row["name"] if name_row else None, floor=body.floor,
        message=body.message, approved_at=approved,
        source=f"Campus Security · {principal.display_name}")


@router.get("/alerts", response_model=list[AlertOut])
def alert_history(_: Principal = Depends(require_security)):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT a.id AS id, a.scope AS scope, a.building_id AS building_id, "
            "b.name AS building_name, a.floor AS floor, a.message AS message, "
            "a.approved_at AS approved_at, u.display_name AS source FROM alert a "
            "LEFT JOIN building b ON b.id=a.building_id "
            "LEFT JOIN app_user u ON u.id=a.approved_by ORDER BY a.approved_at DESC"
        ).fetchall()
    return [AlertOut(id=r["id"], scope=r["scope"], building_id=r["building_id"],
                     building_name=r["building_name"], floor=r["floor"],
                     message=r["message"], approved_at=r["approved_at"],
                     source=f"Campus Security · {r['source']}") for r in rows]
