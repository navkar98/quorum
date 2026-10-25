"""Safety-invariant tests. These encode the non-negotiable guardrails from
.kiro/steering/safety.md. If any of these fail, a core safety property is broken.
"""
from __future__ import annotations

from conftest import sec_headers, student_headers


def _submit(client, device_user, obs, building_id, floor=None, desc="smoke"):
    return client.post(
        "/api/reports",
        headers=student_headers(device_user),
        data={"observation_type": obs, "building_id": building_id,
              "floor": floor if floor is not None else "", "description": desc},
    )


# --- Safety #1: student report isolation ---
def test_students_cannot_list_reports(client):
    _submit(client, 10, "saw", 6, 2, "smoke in lab")
    # Student hitting the security reports endpoint must be forbidden.
    r = client.get("/api/reports", headers=student_headers(10))
    assert r.status_code == 403


# --- Safety #2/#3: aggregate-only Wi-Fi; no identities in security payloads ---
def test_security_payloads_have_no_identities(client):
    _submit(client, 10, "saw", 6, 2, "smoke")
    r = client.get("/api/reports", headers=sec_headers())
    assert r.status_code == 200
    for rep in r.json():
        assert "device_id" not in rep
        assert "reporter_user_id" not in rep


def test_crowd_heatmap_exposes_counts_only(client):
    r = client.get("/api/heatmap/crowd", headers=sec_headers())
    assert r.status_code == 200
    body = r.json()
    text = str(body)
    assert "device_id" not in text and "dev-" not in text and "crowd-isc" not in text
    for b in body["buildings"]:
        assert isinstance(b["total"], int)


# --- Safety #9/#10: distinct-source corroboration, anti-inflation ---
def test_repeated_same_device_does_not_inflate_corroboration(client):
    # One device reports 4 times in the same zone.
    for _ in range(4):
        _submit(client, 10, "saw", 6, 2, "smoke")
    r = client.get("/api/heatmap/incident", headers=sec_headers())
    cell = next(c for c in r.json()["cells"]
                if c["building_id"] == 6 and c["floor"] == 2)
    # Many reports, but only ONE distinct source.
    assert cell["report_count"] >= 4
    assert cell["distinct_sources"] == 1
    # One device alone must not reach potential_impact.
    assert cell["system_assessment"] != "potential_impact"


def test_distinct_devices_do_corroborate(client):
    _submit(client, 10, "saw", 6, 2, "smoke")
    _submit(client, 11, "saw", 6, 2, "haze")
    r = client.get("/api/heatmap/incident", headers=sec_headers())
    cell = next(c for c in r.json()["cells"]
                if c["building_id"] == 6 and c["floor"] == 2)
    assert cell["distinct_sources"] == 2
    assert cell["system_assessment"] == "potential_impact"


# --- Safety #5: only security may change official zone status ---
def test_student_cannot_change_zone_status(client):
    zones = client.get("/api/zones", headers=sec_headers()).json()
    zid = zones[0]["zone_id"]
    r = client.post(f"/api/zones/{zid}/status",
                    headers=student_headers(10),
                    json={"security_status": "cleared"})
    assert r.status_code == 403


def test_security_status_change_writes_history(client):
    zones = client.get("/api/zones", headers=sec_headers()).json()
    zid = zones[0]["zone_id"]
    r = client.post(f"/api/zones/{zid}/status", headers=sec_headers(),
                    json={"security_status": "under_investigation", "note": "check"})
    assert r.status_code == 200
    detail = client.get(f"/api/zones/{zid}", headers=sec_headers()).json()
    assert detail["security_status"] == "under_investigation"
    assert any(h["new_status"] == "under_investigation"
               for h in detail["status_history"])


# --- Safety #4/#6: alert authorization + audit ---
def test_student_cannot_approve_alert(client):
    r = client.post("/api/alerts", headers=student_headers(10),
                    json={"scope": "campus", "message": "test"})
    assert r.status_code == 403


def test_alert_approval_writes_audit(client):
    r = client.post("/api/alerts", headers=sec_headers(),
                    json={"scope": "building", "building_id": 6,
                          "message": "Avoid ISC until further notice."})
    assert r.status_code == 200
    alert_id = r.json()["id"]
    # Audit row must exist for this alert.
    from app.db import get_conn
    with get_conn() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM alert_audit WHERE alert_id=? AND action='approve'",
            (alert_id,),
        ).fetchone()
    assert row["n"] == 1


# --- Safety #12/#13: default-not-safe; negative field obs doesn't clear building ---
def test_new_zone_defaults_unassessed_not_cleared(client):
    zones = client.get("/api/zones", headers=sec_headers()).json()
    for z in zones:
        assert z["security_status"] == "unassessed"
        assert z["system_assessment"] == "insufficient_information"


def test_negative_field_observation_does_not_auto_clear(client):
    # Reports create potential impact.
    _submit(client, 10, "saw", 6, 2, "smoke")
    _submit(client, 11, "saw", 6, 2, "smoke")
    inc = client.post("/api/incidents", headers=sec_headers(),
                      json={"title": "ISC smoke"}).json()
    client.post(f"/api/incidents/{inc['id']}/field-observations", headers=sec_headers(),
                json={"officer_id": "OFC-1", "building_id": 6, "floor": 2,
                      "findings": "no fire, false alarm, all clear"})
    # System assessment may become conflicting_evidence, but security_status must remain
    # whatever security set — never auto-cleared.
    zones = client.get("/api/zones", headers=sec_headers()).json()
    for z in zones:
        if z["building_id"] == 6:
            assert z["security_status"] != "cleared"


# --- Safety #7: AI cannot approve alerts or set status (interface-level) ---
def test_ai_module_has_no_authority_functions(client):
    import app.ai as ai
    exported = dir(ai)
    for forbidden in ("approve_alert", "set_status", "change_status",
                      "publish_alert", "clear_zone"):
        assert forbidden not in exported


# --- Feedback identity protection ---
def test_feedback_results_are_tallies_only(client):
    req = client.post("/api/feedback", headers=sec_headers(),
                      json={"building_id": 6, "floor": 2,
                            "question": "Did you see smoke?"}).json()
    client.post(f"/api/feedback/{req['id']}/respond", headers=student_headers(10),
                json={"answer": "yes"})
    res = client.get(f"/api/feedback/{req['id']}/results", headers=sec_headers()).json()
    assert set(res["tallies"].keys()) == {"yes", "no", "unsure"}
    assert "device_id" not in str(res)
