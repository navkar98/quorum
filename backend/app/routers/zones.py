"""Security-only zone management. Only security can change official status."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from .. import wifi
from ..auth import Principal, require_security
from ..db import get_conn, now_iso
from ..events import publish
from ..models import (FieldObservationOut, StudentAlert, ZoneDetail,
                      ZoneStatusChange, ZoneStatusHistoryOut)
from ..service_reports import serialize_report

router = APIRouter(prefix="/api", tags=["zones"])

VALID_STATUS = {"unassessed", "under_investigation", "restricted", "cleared"}


@router.get("/zones")
def list_zones(_: Principal = Depends(require_security)):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT z.id AS zone_id, z.building_id AS building_id, b.name AS building_name, "
            "z.floor AS floor, za.system_assessment AS system_assessment, "
            "za.security_status AS security_status "
            "FROM zone z JOIN building b ON b.id=z.building_id "
            "JOIN zone_assessment za ON za.zone_id=z.id "
            "ORDER BY z.building_id, z.floor"
        ).fetchall()
    out = []
    for r in rows:
        count, fresh = wifi.zone_device_count(r["zone_id"])
        out.append({**dict(r), "estimated_device_count": count,
                    "device_count_fresh": fresh})
    return out


@router.get("/zones/{zone_id}", response_model=ZoneDetail)
def zone_detail(zone_id: int, _: Principal = Depends(require_security)):
    with get_conn() as conn:
        z = conn.execute(
            "SELECT z.id AS zone_id, z.building_id AS building_id, b.name AS building_name, "
            "z.floor AS floor, za.system_assessment AS system_assessment, "
            "za.security_status AS security_status "
            "FROM zone z JOIN building b ON b.id=z.building_id "
            "JOIN zone_assessment za ON za.zone_id=z.id WHERE z.id=?",
            (zone_id,),
        ).fetchone()
        if z is None:
            raise HTTPException(404, "Zone not found")

        report_rows = conn.execute(
            "SELECT r.id AS id, r.observation_type AS observation_type, "
            "r.building_id AS building_id, b.name AS building_name, r.floor AS floor, "
            "r.description AS description, r.photo_path AS photo_path, "
            "r.created_at AS created_at, r.incident_id AS incident_id "
            "FROM report r JOIN building b ON b.id=r.building_id "
            "WHERE r.building_id=? AND (r.floor IS ? OR ? IS NULL) "
            "ORDER BY r.created_at DESC",
            (z["building_id"], z["floor"], z["floor"]),
        ).fetchall()
        reports = [serialize_report(conn, r) for r in report_rows]

        fo_rows = conn.execute(
            "SELECT id, officer_id, building_id, floor, findings, observed_at "
            "FROM field_observation WHERE building_id=? AND (floor IS ? OR ? IS NULL) "
            "ORDER BY observed_at DESC",
            (z["building_id"], z["floor"], z["floor"]),
        ).fetchall()
        field_obs = [FieldObservationOut(**dict(r)) for r in fo_rows]

        # Feedback tallies for requests on this building/floor (counts only).
        tally = {"yes": 0, "no": 0, "unsure": 0}
        fb = conn.execute(
            "SELECT fres.answer AS answer, COUNT(*) AS n FROM feedback_response fres "
            "JOIN feedback_request freq ON freq.id=fres.request_id "
            "WHERE freq.building_id=? AND (freq.floor IS ? OR ? IS NULL) "
            "GROUP BY fres.answer",
            (z["building_id"], z["floor"], z["floor"]),
        ).fetchall()
        for row in fb:
            tally[row["answer"]] = row["n"]

        alert_rows = conn.execute(
            "SELECT a.id AS id, a.scope AS scope, b.name AS building_name, a.floor AS floor, "
            "a.message AS message, a.approved_at AS approved_at, u.display_name AS source "
            "FROM alert a LEFT JOIN building b ON b.id=a.building_id "
            "LEFT JOIN app_user u ON u.id=a.approved_by "
            "WHERE a.scope='campus' OR a.building_id=? ORDER BY a.approved_at DESC",
            (z["building_id"],),
        ).fetchall()
        alerts = [StudentAlert(id=r["id"], scope=r["scope"],
                               building_name=r["building_name"], floor=r["floor"],
                               message=r["message"],
                               source=f"Campus Security · {r['source']}",
                               issued_at=r["approved_at"]) for r in alert_rows]

        hist_rows = conn.execute(
            "SELECT old_status, new_status, changed_at, note FROM zone_status_history "
            "WHERE zone_id=? ORDER BY changed_at DESC",
            (zone_id,),
        ).fetchall()
        history = [ZoneStatusHistoryOut(**dict(r)) for r in hist_rows]

    count, fresh = wifi.zone_device_count(zone_id)
    return ZoneDetail(
        zone_id=z["zone_id"], building_id=z["building_id"],
        building_name=z["building_name"], floor=z["floor"],
        system_assessment=z["system_assessment"],
        security_status=z["security_status"],
        estimated_device_count=count, device_count_fresh=fresh,
        reports=reports, field_observations=field_obs,
        feedback_tallies=tally, alert_history=alerts, status_history=history,
    )


@router.post("/zones/{zone_id}/status")
def change_status(zone_id: int, body: ZoneStatusChange,
                  principal: Principal = Depends(require_security)):
    """Only security may change official zone status. Writes history + audit."""
    if body.security_status not in VALID_STATUS:
        raise HTTPException(422, "Invalid status")
    with get_conn() as conn:
        cur = conn.execute(
            "SELECT security_status FROM zone_assessment WHERE zone_id=?", (zone_id,)
        ).fetchone()
        if cur is None:
            raise HTTPException(404, "Zone not found")
        old = cur["security_status"]
        changed = now_iso()
        conn.execute(
            "UPDATE zone_assessment SET security_status=?, updated_by=?, updated_at=? "
            "WHERE zone_id=?",
            (body.security_status, principal.user_id, changed, zone_id),
        )
        conn.execute(
            "INSERT INTO zone_status_history(zone_id, old_status, new_status, "
            "changed_by, changed_at, note) VALUES (?,?,?,?,?,?)",
            (zone_id, old, body.security_status, principal.user_id, changed, body.note),
        )
    publish("zone.updated", {"zone_id": zone_id,
                             "security_status": body.security_status})
    return {"status": "updated", "old": old, "new": body.security_status}
