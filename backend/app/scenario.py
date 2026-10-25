"""Synthetic scenario replay. Emits reports and field observations chronologically so
the demo shows data arriving live. Uses only simulated data and never touches real
infrastructure. A real phone can submit reports concurrently.
"""
from __future__ import annotations

import asyncio
import json

from . import config
from .db import get_conn
from .events import publish
from .evidence import apply_assessments
from .service_reports import create_report, run_analysis

_task: asyncio.Task | None = None
_state = {"running": False, "sent": 0, "total": 0, "title": None}

# Speed factor: compress offsets so the demo runs quickly (e.g. 10x faster).
SPEED = float(__import__("os").environ.get("QUORUM_SCENARIO_SPEED", "10"))


def status() -> dict:
    return dict(_state)


def _load_scenario() -> dict:
    return json.loads((config.SEED_DIR / "scenario.json").read_text(encoding="utf-8"))


async def _run() -> None:
    data = _load_scenario()
    events = sorted(data["events"], key=lambda e: e["offset_sec"])
    _state.update(running=True, sent=0, total=len(events), title=data["title"])
    publish("scenario.started", {"title": data["title"], "total": len(events)})

    prev = 0
    try:
        for ev in events:
            delay = max(0.0, (ev["offset_sec"] - prev) / SPEED)
            prev = ev["offset_sec"]
            if delay:
                await asyncio.sleep(delay)

            if ev["type"] == "report":
                result = create_report(
                    reporter_user_id=ev.get("reporter_user_id"),
                    device_id=ev.get("device_id"),
                    observation_type=ev["observation_type"],
                    building_id=ev["building_id"],
                    floor=ev.get("floor"),
                    description=ev.get("description"),
                    photo_path=None,
                )
                run_analysis(result["id"])
            elif ev["type"] == "field_observation":
                with get_conn() as conn:
                    inc = conn.execute(
                        "SELECT id FROM incident ORDER BY created_at DESC LIMIT 1"
                    ).fetchone()
                    from .db import now_iso
                    conn.execute(
                        "INSERT INTO field_observation(incident_id, officer_id, "
                        "building_id, floor, findings, observed_at, created_at) "
                        "VALUES (?,?,?,?,?,?,?)",
                        (inc["id"] if inc else None, ev["officer_id"], ev["building_id"],
                         ev.get("floor"), ev["findings"], now_iso(), now_iso()),
                    )
                for u in apply_assessments():
                    publish("zone.updated", u)
                publish("field_observation.created", {"scenario": True})

            _state["sent"] += 1
            publish("scenario.progress", {"sent": _state["sent"],
                                          "total": _state["total"]})
    finally:
        _state["running"] = False
        publish("scenario.finished", {"sent": _state["sent"]})


async def start() -> dict:
    global _task
    if _task and not _task.done():
        return {"status": "already_running", **status()}
    _task = asyncio.create_task(_run())
    return {"status": "started"}


async def stop() -> dict:
    global _task
    if _task and not _task.done():
        _task.cancel()
        _state["running"] = False
        return {"status": "stopped"}
    return {"status": "not_running"}


# Tables cleared on a demo reset. Order matters for foreign keys: children first.
_RESET_TABLES = [
    "report_analysis",
    "field_observation",
    "feedback_response",
    "feedback_request",
    "alert_audit",
    "alert",
    "zone_status_history",
    "report",
    "incident",
]


async def reset() -> dict:
    """Clear all demo/transactional data and restore safe default zone assessments.

    Removes reports, analyses, incidents, field observations, feedback, alerts, and zone
    status history, then resets every zone to the safe defaults (security_status
    'unassessed', system_assessment 'insufficient_information'). Structural seed data —
    buildings, zones, users, and simulated Wi-Fi associations — is preserved so the demo
    can be run again immediately. Any running scenario is stopped first.
    """
    global _task
    if _task and not _task.done():
        _task.cancel()
    _state.update(running=False, sent=0, total=0, title=None)

    with get_conn() as conn:
        for table in _RESET_TABLES:
            conn.execute(f"DELETE FROM {table}")
        # Restore the safe defaults for every zone. Never leaves a zone 'cleared'.
        conn.execute(
            "UPDATE zone_assessment SET security_status='unassessed', "
            "system_assessment='insufficient_information', updated_by=NULL, "
            "updated_at=NULL"
        )

    publish("scenario.reset", {})
    return {"status": "reset"}
