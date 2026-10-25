"""Seed loader for synthetic data.

Loads buildings and users, generates zones (one per floor plus a whole-building zone),
seeds simulated Wi-Fi associations and zone assessments. The scenario timeline is NOT
loaded here; it is replayed live by scenario.py so the demo shows data arriving.

Run:  python -m app.seed       (from backend/)
      python -m app.seed --reset   to drop and recreate the DB file
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone

from . import config
from .db import get_conn, init_schema, now_iso


def _load(name: str):
    return json.loads((config.SEED_DIR / name).read_text(encoding="utf-8"))


def seed() -> None:
    init_schema()
    buildings = _load("buildings.json")
    users = _load("users.json")
    wifi = _load("wifi_associations.json")

    with get_conn() as conn:
        # Buildings
        for b in buildings:
            conn.execute(
                "INSERT OR IGNORE INTO building(id, name, floors) VALUES (?,?,?)",
                (b["id"], b["name"], b["floors"]),
            )
        # Zones: whole-building (floor NULL) + one per floor
        for b in buildings:
            conn.execute(
                "INSERT OR IGNORE INTO zone(building_id, floor) VALUES (?, NULL)",
                (b["id"],),
            )
            for fl in range(1, b["floors"] + 1):
                conn.execute(
                    "INSERT OR IGNORE INTO zone(building_id, floor) VALUES (?,?)",
                    (b["id"], fl),
                )
        # Users
        for u in users:
            conn.execute(
                "INSERT OR IGNORE INTO app_user(id, role, display_name, device_id) "
                "VALUES (?,?,?,?)",
                (u["id"], u["role"], u["display_name"], u.get("device_id")),
            )
        # Default zone assessments (unassessed / insufficient_information)
        zones = conn.execute("SELECT id FROM zone").fetchall()
        for z in zones:
            conn.execute(
                "INSERT OR IGNORE INTO zone_assessment(zone_id) VALUES (?)",
                (z["id"],),
            )
        # Simulated Wi-Fi associations (backend-only)
        now = datetime.now(timezone.utc)
        for w in wifi:
            zone = conn.execute(
                "SELECT id FROM zone WHERE building_id=? AND "
                "((floor IS NULL AND ? IS NULL) OR floor=?)",
                (w["building_id"], w.get("floor"), w.get("floor")),
            ).fetchone()
            if zone is None:
                continue
            observed = (now + timedelta(minutes=w.get("offset_min", 0))).isoformat()
            conn.execute(
                "INSERT INTO wifi_association(device_id, zone_id, confidence, "
                "observed_at, stale) VALUES (?,?,?,?,?)",
                (w["device_id"], zone["id"], w["confidence"], observed,
                 int(w.get("stale", 0))),
            )
    print(f"Seeded {len(buildings)} buildings, {len(users)} users, "
          f"{len(wifi)} wifi associations at {now_iso()}")


def reset() -> None:
    if config.DB_PATH.exists():
        config.DB_PATH.unlink()
        print(f"Removed {config.DB_PATH}")


if __name__ == "__main__":
    if "--reset" in sys.argv:
        reset()
    seed()
