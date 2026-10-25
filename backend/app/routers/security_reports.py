"""Security-only: reports, incidents, field observations. Identities never exposed."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ..auth import Principal, require_security
from ..db import get_conn, now_iso
from ..events import publish
from ..evidence import apply_assessments
from ..models import (AttachReports, FieldObservationCreate, FieldObservationOut,
                      IncidentCreate, IncidentOut, ReportOut)
from ..service_reports import serialize_report

router = APIRouter(prefix="/api", tags=["security"])

_REPORT_SELECT = (
    "SELECT r.id AS id, r.observation_type AS observation_type, "
    "r.building_id AS building_id, b.name AS building_name, r.floor AS floor, "
    "r.description AS description, r.photo_path AS photo_path, "
    "r.created_at AS created_at, r.incident_id AS incident_id "
    "FROM report r JOIN building b ON b.id = r.building_id "
)


@router.get("/reports", response_model=list[ReportOut])
def list_reports(_: Principal = Depends(require_security)):
    with get_conn() as conn:
        rows = conn.execute(_REPORT_SELECT + "ORDER BY r.created_at DESC").fetchall()
        return [serialize_report(conn, r) for r in rows]


@router.get("/incidents", response_model=list[IncidentOut])
def list_incidents(_: Principal = Depends(require_security)):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, title, status, created_at FROM incident ORDER BY created_at DESC"
        ).fetchall()
    return [IncidentOut(**dict(r)) for r in rows]


@router.post("/incidents", response_model=IncidentOut)
def create_incident(body: IncidentCreate, principal: Principal = Depends(require_security)):
    created = now_iso()
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO incident(title, status, created_by, created_at) "
            "VALUES (?,?,?,?)",
            (body.title, "open", principal.user_id, created),
        )
        iid = cur.lastrowid
    publish("incident.created", {"incident_id": iid})
    return IncidentOut(id=iid, title=body.title, status="open", created_at=created)


@router.post("/incidents/{incident_id}/attach")
def attach_reports(incident_id: int, body: AttachReports,
                   _: Principal = Depends(require_security)):
    with get_conn() as conn:
        if not conn.execute("SELECT 1 FROM incident WHERE id=?", (incident_id,)).fetchone():
            raise HTTPException(404, "Incident not found")
        for rid in body.report_ids:
            conn.execute("UPDATE report SET incident_id=? WHERE id=?", (incident_id, rid))
    publish("incident.updated", {"incident_id": incident_id})
    return {"status": "attached", "count": len(body.report_ids)}


@router.get("/incidents/{incident_id}/reports", response_model=list[ReportOut])
def incident_reports(incident_id: int, _: Principal = Depends(require_security)):
    with get_conn() as conn:
        rows = conn.execute(
            _REPORT_SELECT + "WHERE r.incident_id=? ORDER BY r.created_at ASC",
            (incident_id,),
        ).fetchall()
        return [serialize_report(conn, r) for r in rows]


@router.post("/incidents/{incident_id}/field-observations",
             response_model=FieldObservationOut)
def add_field_observation(incident_id: int, body: FieldObservationCreate,
                          _: Principal = Depends(require_security)):
    observed = body.observed_at or now_iso()
    created = now_iso()
    with get_conn() as conn:
        if not conn.execute("SELECT 1 FROM incident WHERE id=?", (incident_id,)).fetchone():
            raise HTTPException(404, "Incident not found")
        cur = conn.execute(
            "INSERT INTO field_observation(incident_id, officer_id, building_id, floor, "
            "findings, observed_at, created_at) VALUES (?,?,?,?,?,?,?)",
            (incident_id, body.officer_id, body.building_id, body.floor,
             body.findings, observed, created),
        )
        fid = cur.lastrowid
    # New information → recompute assessments (may surface a contradiction).
    for u in apply_assessments():
        publish("zone.updated", u)
    publish("field_observation.created", {"incident_id": incident_id})
    return FieldObservationOut(
        id=fid, officer_id=body.officer_id, building_id=body.building_id,
        floor=body.floor, findings=body.findings, observed_at=observed)
