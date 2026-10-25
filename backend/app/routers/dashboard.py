"""Security-only dashboard: two separate heatmaps, map metadata, SSE stream."""
from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from .. import config, wifi
from ..auth import Principal, get_principal, require_security
from ..db import get_conn
from ..events import event_stream, subscribe

router = APIRouter(prefix="/api", tags=["dashboard"])


@router.get("/map")
def campus_map(_: Principal = Depends(require_security)):
    data = json.loads((config.SEED_DIR / "campus_map.json").read_text(encoding="utf-8"))
    return data


@router.get("/demo/recipients")
def demo_recipients(scope: str, building_id: int | None = None,
                    floor: int | None = None,
                    _: Principal = Depends(require_security)):
    """DEMO-ONLY preview: which seeded student accounts would receive a push for this
    target. Lets a presenter verify push targeting by signing in as exactly those
    students. Returns display names only (no device ids). Not a production feature.
    """
    students = wifi.demo_recipients(
        building_id=building_id, floor=floor, campus=(scope == "campus"))
    return {"scope": scope, "building_id": building_id, "floor": floor,
            "recipients": students, "count": len(students)}


@router.get("/heatmap/incident")
def incident_heatmap(_: Principal = Depends(require_security)):
    """Heatmap 1: concentrations of recent student reports. Reported != confirmed.

    Uses the evidence engine so clusters, distinct-source corroboration, contradiction
    and duplicate flags are surfaced — density alone is never treated as danger.
    """
    from ..evidence import correlate
    clusters = correlate()
    out = []
    for c in clusters:
        out.append({
            "building_id": c.building_id,
            "floor": c.floor,
            "report_count": len(c.report_ids),
            "distinct_sources": c.distinct_sources,
            "firsthand_sources": c.firsthand_sources,
            "hazards": c.hazards,
            "duplicate_count": len(c.duplicate_report_ids),
            "contradiction": c.contradiction,
            "system_assessment": c.system_assessment,
        })
    return {"mode": "incident_activity",
            "note": "Report density does not prove danger.",
            "cells": out}


@router.get("/heatmap/crowd")
def crowd_heatmap(_: Principal = Depends(require_security)):
    """Heatmap 2: estimated Wi-Fi device counts by building/floor. Counts != occupancy,
    and crowd density does not prove safety. Aggregate counts only — no identities.
    """
    return {"mode": "crowd_density",
            "note": "Estimated connected devices; not exact occupancy; does not prove safety.",
            "buildings": wifi.crowd_by_building()}


@router.get("/dashboard/summary")
def dashboard_summary(_: Principal = Depends(require_security)):
    with get_conn() as conn:
        recent = conn.execute(
            "SELECT r.id AS id, r.observation_type AS t, b.name AS building, "
            "r.floor AS floor, r.created_at AS created_at FROM report r "
            "JOIN building b ON b.id=r.building_id ORDER BY r.created_at DESC LIMIT 10"
        ).fetchall()
        incidents = conn.execute(
            "SELECT COUNT(*) AS n FROM incident WHERE status!='closed'"
        ).fetchone()["n"]
        to_review = conn.execute(
            "SELECT COUNT(*) AS n FROM zone_assessment "
            "WHERE system_assessment IN ('potential_impact','conflicting_evidence')"
        ).fetchone()["n"]
    return {
        "active_incidents": incidents,
        "zones_to_review": to_review,
        "recent_reports": [dict(r) for r in recent],
    }


@router.get("/events")
async def events(request: Request, authorization: str | None = None):
    # SSE clients (EventSource) cannot set custom headers, so accept a token query param
    # too. Validate role before streaming.
    token = request.query_params.get("token")
    auth_header = f"Bearer {token}" if token else authorization
    principal = get_principal(auth_header)
    if not principal.is_security:
        from fastapi import HTTPException
        raise HTTPException(403, "Security role required")

    sub = subscribe()  # broadcast: dashboard receives every event

    async def gen():
        async for chunk in event_stream(sub):
            if await request.is_disconnected():
                break
            yield chunk

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache",
                                      "X-Accel-Buffering": "no"})
