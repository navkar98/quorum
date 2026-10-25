"""Simulated Wi-Fi zone identification.

Device-to-zone associations are backend-only. This module exposes:
  - a per-device location suggestion (building/floor + confidence/staleness)
  - aggregate per-zone device counts with freshness

It NEVER returns device identities through any function used by security endpoints.
Aggregate helpers return counts only.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from . import config
from .db import get_conn


def suggest_for_device(device_id: str | None) -> dict:
    """Latest association for a device → suggested building/floor."""
    if not device_id:
        return _unavailable()
    with get_conn() as conn:
        row = conn.execute(
            "SELECT b.id AS building_id, b.name AS building_name, z.floor AS floor, "
            "       w.confidence AS confidence, w.stale AS stale "
            "FROM wifi_association w "
            "JOIN zone z ON z.id = w.zone_id "
            "JOIN building b ON b.id = z.building_id "
            "WHERE w.device_id = ? "
            "ORDER BY w.observed_at DESC LIMIT 1",
            (device_id,),
        ).fetchone()
    if row is None:
        return _unavailable()
    low_conf = row["confidence"] < 0.5 or bool(row["stale"])
    return {
        "building_id": row["building_id"],
        "building_name": row["building_name"],
        "floor": row["floor"],
        "confidence": round(row["confidence"], 2),
        "stale": bool(row["stale"]),
        "available": not low_conf,
    }


def _unavailable() -> dict:
    return {
        "building_id": None,
        "building_name": None,
        "floor": None,
        "confidence": 0.0,
        "stale": True,
        "available": False,
    }


def demo_recipients(building_id: int | None, floor: int | None,
                    campus: bool = False) -> list[dict]:
    """DEMO-ONLY. Return the seeded *student* accounts whose current simulated zone
    matches a target, so a presenter can verify push targeting from the sign-in list.

    This intentionally exposes student display names and is NOT a production feature:
    real deployments must never reveal which identified people are in a zone. It is used
    only by the demo recipients-preview endpoint and never by the core dashboards. Device
    identifiers are still never returned.
    """
    with get_conn() as conn:
        if campus:
            rows = conn.execute(
                "SELECT id, display_name, device_id FROM app_user "
                "WHERE role='student' AND device_id IS NOT NULL"
            ).fetchall()
            return [{"id": r["id"], "display_name": r["display_name"]} for r in rows]

        students = conn.execute(
            "SELECT id, display_name, device_id FROM app_user "
            "WHERE role='student' AND device_id IS NOT NULL"
        ).fetchall()

    out = []
    for s in students:
        loc = suggest_for_device(s["device_id"])
        if loc.get("building_id") != building_id:
            continue
        if floor is not None and loc.get("floor") != floor:
            continue
        out.append({"id": s["id"], "display_name": s["display_name"]})
    return out


def eligible_devices(building_id: int, floor: int | None) -> list[str]:
    """Backend-only: distinct device ids associated with a building/floor.

    Used solely for notification routing and audience counts. Never returned to
    security-facing responses.
    """
    with get_conn() as conn:
        if floor is None:
            rows = conn.execute(
                "SELECT DISTINCT w.device_id AS d FROM wifi_association w "
                "JOIN zone z ON z.id = w.zone_id WHERE z.building_id = ?",
                (building_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT DISTINCT w.device_id AS d FROM wifi_association w "
                "JOIN zone z ON z.id = w.zone_id "
                "WHERE z.building_id = ? AND z.floor = ?",
                (building_id, floor),
            ).fetchall()
    return [r["d"] for r in rows]


def eligible_count(building_id: int | None, floor: int | None, campus: bool = False) -> int:
    """Aggregate audience size. Counts distinct devices only — no identities."""
    with get_conn() as conn:
        if campus:
            row = conn.execute(
                "SELECT COUNT(DISTINCT device_id) AS n FROM wifi_association"
            ).fetchone()
        elif floor is None:
            row = conn.execute(
                "SELECT COUNT(DISTINCT w.device_id) AS n FROM wifi_association w "
                "JOIN zone z ON z.id = w.zone_id WHERE z.building_id = ?",
                (building_id,),
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT COUNT(DISTINCT w.device_id) AS n FROM wifi_association w "
                "JOIN zone z ON z.id = w.zone_id WHERE z.building_id=? AND z.floor=?",
                (building_id, floor),
            ).fetchone()
    return int(row["n"]) if row else 0


def zone_device_count(zone_id: int) -> tuple[int, bool]:
    """(estimated distinct device count, is_fresh) for a zone. Counts only."""
    fresh_cutoff = (
        datetime.now(timezone.utc) - timedelta(minutes=config.WIFI_FRESH_MIN)
    ).isoformat()
    with get_conn() as conn:
        total = conn.execute(
            "SELECT COUNT(DISTINCT device_id) AS n FROM wifi_association WHERE zone_id=?",
            (zone_id,),
        ).fetchone()["n"]
        recent = conn.execute(
            "SELECT COUNT(DISTINCT device_id) AS n FROM wifi_association "
            "WHERE zone_id=? AND stale=0 AND observed_at >= ?",
            (zone_id, fresh_cutoff),
        ).fetchone()["n"]
    return int(total), bool(recent > 0)


def crowd_by_building() -> list[dict]:
    """Aggregate crowd density per building and per floor. Counts only, with freshness
    and an unknown/unassociated indicator.
    """
    fresh_cutoff = (
        datetime.now(timezone.utc) - timedelta(minutes=config.WIFI_FRESH_MIN)
    ).isoformat()
    with get_conn() as conn:
        buildings = conn.execute("SELECT id, name, floors FROM building").fetchall()
        out = []
        for b in buildings:
            floors = []
            for fl in range(1, b["floors"] + 1):
                z = conn.execute(
                    "SELECT id FROM zone WHERE building_id=? AND floor=?",
                    (b["id"], fl),
                ).fetchone()
                count, fresh = (0, False)
                if z:
                    count, fresh = zone_device_count(z["id"])
                floors.append({"floor": fl, "count": count, "fresh": fresh})
            stale = conn.execute(
                "SELECT COUNT(DISTINCT w.device_id) AS n FROM wifi_association w "
                "JOIN zone z ON z.id=w.zone_id "
                "WHERE z.building_id=? AND (w.stale=1 OR w.observed_at < ?)",
                (b["id"], fresh_cutoff),
            ).fetchone()["n"]
            total = sum(f["count"] for f in floors)
            out.append({
                "building_id": b["id"],
                "building_name": b["name"],
                "total": total,
                "floors": floors,
                "stale_or_unknown": int(stale),
            })
        return out
