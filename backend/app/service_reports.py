"""Shared report helpers: creation, async analysis, security-safe serialization."""
from __future__ import annotations

import json

from . import ai, evidence
from .db import get_conn, now_iso
from .events import publish
from .models import ReportAnalysisOut, ReportOut


def create_report(reporter_user_id: int | None, device_id: str | None,
                  observation_type: str, building_id: int, floor: int | None,
                  description: str | None, photo_path: str | None) -> dict:
    created = now_iso()
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO report(reporter_user_id, device_id, observation_type, "
            "building_id, floor, description, photo_path, created_at) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (reporter_user_id, device_id, observation_type, building_id, floor,
             description, photo_path, created),
        )
        report_id = cur.lastrowid
    # Notify dashboards immediately (no identity in payload).
    publish("report.created", {
        "report_id": report_id,
        "building_id": building_id,
        "floor": floor,
        "observation_type": observation_type,
        "created_at": created,
    })
    return {"id": report_id, "created_at": created}


def run_analysis(report_id: int) -> None:
    """Background task: AI/rules analysis + evidence flags. Never blocks submission."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT description, photo_path FROM report WHERE id=?", (report_id,)
        ).fetchone()
    if row is None:
        return
    result = ai.analyze(row["description"], row["photo_path"])
    flags = evidence.duplicate_and_contradiction_flags().get(report_id, {})

    with get_conn() as conn:
        conn.execute(
            "INSERT INTO report_analysis(report_id, kind, summary, distress_indicators, "
            "hazards, contradiction_flag, duplicate_flag, source_refs, created_at) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (
                report_id, result.kind, result.summary,
                json.dumps(result.distress_indicators),
                json.dumps(result.hazards),
                int(flags.get("contradiction_flag", False)),
                int(flags.get("duplicate_flag", False)),
                json.dumps(flags.get("source_refs", []) + result.source_refs),
                now_iso(),
            ),
        )
    # Recompute system assessments as new info arrived.
    updated = evidence.apply_assessments()
    publish("analysis.updated", {"report_id": report_id, "kind": result.kind})
    for u in updated:
        publish("zone.updated", u)


def _latest_analysis(conn, report_id: int) -> ReportAnalysisOut | None:
    a = conn.execute(
        "SELECT kind, summary, distress_indicators, hazards, contradiction_flag, "
        "duplicate_flag, source_refs FROM report_analysis "
        "WHERE report_id=? ORDER BY created_at DESC LIMIT 1",
        (report_id,),
    ).fetchone()
    if a is None:
        return None
    return ReportAnalysisOut(
        kind=a["kind"],
        summary=a["summary"],
        distress_indicators=json.loads(a["distress_indicators"] or "[]"),
        hazards=json.loads(a["hazards"] or "[]"),
        contradiction_flag=bool(a["contradiction_flag"]),
        duplicate_flag=bool(a["duplicate_flag"]),
        source_refs=json.loads(a["source_refs"] or "[]"),
    )


def serialize_report(conn, row) -> ReportOut:
    """Build a security-safe ReportOut. Deliberately omits reporter identity/device."""
    return ReportOut(
        id=row["id"],
        observation_type=row["observation_type"],
        building_id=row["building_id"],
        building_name=row["building_name"],
        floor=row["floor"],
        description=row["description"],
        has_photo=bool(row["photo_path"]),
        created_at=row["created_at"],
        incident_id=row["incident_id"],
        analysis=_latest_analysis(conn, row["id"]),
    )
