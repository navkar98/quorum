"""Tests for zone-targeted student push delivery.

The audience predicate must forward feedback/alert pushes only to students whose current
simulated zone matches the target (plus campus-wide alerts), and must never leak
identities. These checks protect safety rules #2/#3 (no identity exposure) and the
targeting contract.
"""
from __future__ import annotations

from app.routers.student import _ZoneAudience


# Seeded: device dev-a1 -> ISC (building 6) floor 2; dev-e5 -> Healey (building 2) fl 4.
def test_feedback_push_matches_same_building_floor(client):
    aud = _ZoneAudience("dev-a1")  # ISC floor 2
    assert aud("feedback.created", {"building_id": 6, "floor": 2}) is True


def test_feedback_push_rejects_other_building(client):
    aud = _ZoneAudience("dev-a1")  # ISC floor 2
    assert aud("feedback.created", {"building_id": 2, "floor": 4}) is False


def test_feedback_push_rejects_other_floor(client):
    aud = _ZoneAudience("dev-a1")  # ISC floor 2
    assert aud("feedback.created", {"building_id": 6, "floor": 3}) is False


def test_building_wide_push_matches_any_floor_in_building(client):
    aud = _ZoneAudience("dev-a1")  # ISC floor 2
    # floor=None means whole building -> matches the student in that building.
    assert aud("feedback.created", {"building_id": 6, "floor": None}) is True


def test_campus_alert_reaches_everyone(client):
    aud = _ZoneAudience("dev-e5")  # library
    assert aud("alert.created", {"scope": "campus", "building_id": None, "floor": None}) is True


def test_building_alert_only_matches_that_building(client):
    aud_isc = _ZoneAudience("dev-a1")   # ISC
    aud_lib = _ZoneAudience("dev-e5")   # library
    evt = {"scope": "building", "building_id": 6, "floor": None}
    assert aud_isc("alert.created", evt) is True
    assert aud_lib("alert.created", evt) is False


def test_non_push_event_types_are_ignored(client):
    aud = _ZoneAudience("dev-a1")
    # Dashboard-only events must never be forwarded to students.
    assert aud("report.created", {"building_id": 6, "floor": 2}) is False
    assert aud("zone.updated", {"building_id": 6}) is False


def test_device_without_zone_gets_only_campus(client):
    aud = _ZoneAudience(None)  # no device / no zone
    assert aud("feedback.created", {"building_id": 6, "floor": 2}) is False
    assert aud("alert.created", {"scope": "campus"}) is True


# --- Demo recipients preview (verifies the sign-in targeting aid) ---
from conftest import sec_headers  # noqa: E402


def test_recipients_floor_scope_lists_only_matching_students(client):
    # Seed: students 10 & 11 are on ISC (building 6) floor 2.
    r = client.get("/api/demo/recipients?scope=floor&building_id=6&floor=2",
                   headers=sec_headers())
    assert r.status_code == 200
    names = {s["display_name"] for s in r.json()["recipients"]}
    assert names == {"Student 10", "Student 11"}


def test_recipients_building_scope_includes_other_floors(client):
    # Building 6 (ISC): students 10, 11 (fl2) and 12 (fl1).
    r = client.get("/api/demo/recipients?scope=building&building_id=6",
                   headers=sec_headers())
    names = {s["display_name"] for s in r.json()["recipients"]}
    assert names == {"Student 10", "Student 11", "Student 12"}


def test_recipients_campus_scope_includes_all_students(client):
    r = client.get("/api/demo/recipients?scope=campus", headers=sec_headers())
    assert r.json()["count"] == 6


def test_recipients_endpoint_requires_security(client):
    r = client.get("/api/demo/recipients?scope=campus",
                   headers={"Authorization": "Bearer quorum-10"})
    assert r.status_code == 403


def test_recipients_never_returns_device_ids(client):
    r = client.get("/api/demo/recipients?scope=building&building_id=6",
                   headers=sec_headers())
    assert "device_id" not in str(r.json())
    assert "dev-" not in str(r.json())
