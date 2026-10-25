"""Quorum FastAPI application entrypoint."""
from __future__ import annotations

from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from . import ai, config, db
from .db import get_conn
from .routers import (alerts, dashboard, feedback, scenario, security_reports,
                      student, zones)

app = FastAPI(title="Quorum", version="0.1.0",
              description="AI-assisted campus emergency coordination (hackathon prototype)")

# Permissive CORS for local dev (student phone + security desktop on the LAN).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup() -> None:
    db.init_schema()
    if not db.has_data():
        # Auto-seed on first run so the demo is one command.
        from . import seed as seed_mod
        seed_mod.seed()


meta = APIRouter(prefix="/api", tags=["meta"])


@meta.get("/health")
def health():
    return {"status": "ok", "ai_provider": ai.get_provider_name()}


@meta.get("/buildings")
def buildings():
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, name, floors FROM building ORDER BY id"
        ).fetchall()
    return [dict(r) for r in rows]


@meta.get("/session/{user_id}")
def session(user_id: int):
    """Demo login helper: returns a token + role for a seeded user. In production this
    would be a real auth flow.
    """
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id, role, display_name FROM app_user WHERE id=?", (user_id,)
        ).fetchone()
    if row is None:
        raise HTTPException(404, "Unknown user")
    return {"token": f"quorum-{row['id']}", "role": row["role"],
            "display_name": row["display_name"]}


@meta.get("/users")
def users():
    """List seeded demo users for the demo login screen. For students, include their
    estimated Wi-Fi location (building/floor) so the picker can show where each demo
    student currently is. This is the student's own suggested location — the same value
    they'd see after signing in — not another person's data.
    """
    from . import wifi
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, role, display_name, device_id FROM app_user ORDER BY role, id"
        ).fetchall()
    out = []
    for r in rows:
        item = {"id": r["id"], "role": r["role"], "display_name": r["display_name"]}
        if r["role"] == "student":
            s = wifi.suggest_for_device(r["device_id"])
            item["location"] = {
                "building_name": s.get("building_name"),
                "floor": s.get("floor"),
                "available": s.get("available", False),
                "stale": s.get("stale", True),
            }
        out.append(item)
    return out


app.include_router(meta)
app.include_router(student.router)
app.include_router(security_reports.router)
app.include_router(zones.router)
app.include_router(feedback.router)
app.include_router(alerts.router)
app.include_router(dashboard.router)
app.include_router(scenario.router)
