"""End-to-end flow test mirroring the hackathon demo script (Req 14.3):
reports -> dashboard -> incident heatmap -> crowd heatmap -> AI/rules cluster +
contradiction -> dispatcher field observation -> updated assessment -> manual zone
status change -> targeted feedback -> approved zone alert -> student receives alert.
"""
from __future__ import annotations

from conftest import sec_headers, student_headers


def _submit(client, user_id, obs, building_id, floor, desc):
    return client.post("/api/reports", headers=student_headers(user_id),
                       data={"observation_type": obs, "building_id": building_id,
                             "floor": floor, "description": desc})


def test_full_demo_flow(client):
    # 1-2. Students submit reports; they appear to security.
    _submit(client, 10, "saw", 6, 2, "smoke in the lab, burning plastic smell")
    _submit(client, 11, "saw", 6, 2, "haze in the hallway")
    _submit(client, 12, "heard", 6, 1, "heard an alarm and people saying smoke")
    reports = client.get("/api/reports", headers=sec_headers()).json()
    assert len(reports) >= 3

    # 3. Incident heatmap updates and clusters the ISC reports.
    inc_heat = client.get("/api/heatmap/incident", headers=sec_headers()).json()
    isc_cell = next(c for c in inc_heat["cells"] if c["building_id"] == 6 and c["floor"] == 2)
    assert isc_cell["distinct_sources"] == 2
    assert isc_cell["system_assessment"] == "potential_impact"

    # 4. Crowd heatmap shows aggregate device distribution (counts only).
    crowd = client.get("/api/heatmap/crowd", headers=sec_headers()).json()
    assert any(b["total"] > 0 for b in crowd["buildings"])

    # 5. AI/rules analysis present and labeled.
    with_analysis = [r for r in reports if r["analysis"]]
    assert with_analysis and with_analysis[0]["analysis"]["kind"] in ("ai", "rules")

    # 6. Dispatcher enters a radio field observation that conflicts with reports.
    inc = client.post("/api/incidents", headers=sec_headers(),
                      json={"title": "ISC possible smoke"}).json()
    client.post(f"/api/incidents/{inc['id']}/field-observations", headers=sec_headers(),
                json={"officer_id": "OFC-204", "building_id": 6, "floor": 2,
                      "findings": "light haze from a hotplate, no active fire, no injuries"})

    # 7. Assessment updates -> conflicting_evidence for that zone.
    inc_heat2 = client.get("/api/heatmap/incident", headers=sec_headers()).json()
    isc_cell2 = next(c for c in inc_heat2["cells"] if c["building_id"] == 6 and c["floor"] == 2)
    assert isc_cell2["system_assessment"] == "conflicting_evidence"
    assert isc_cell2["contradiction"] is True

    # 8. Security manually updates the official zone status.
    zones = client.get("/api/zones", headers=sec_headers()).json()
    isc_zone = next(z for z in zones if z["building_id"] == 6 and z["floor"] == 2)
    r = client.post(f"/api/zones/{isc_zone['zone_id']}/status", headers=sec_headers(),
                    json={"security_status": "under_investigation", "note": "officer en route"})
    assert r.status_code == 200

    # 9. Security requests targeted feedback; eligible count returned.
    fb = client.post("/api/feedback", headers=sec_headers(),
                     json={"building_id": 6, "floor": 2,
                           "question": "Did you personally observe smoke?"}).json()
    assert fb["eligible_device_count"] >= 1

    # 10. Security approves a building-scoped alert.
    alert = client.post("/api/alerts", headers=sec_headers(),
                        json={"scope": "building", "building_id": 6,
                              "message": "Avoid the Integrated Sciences Complex until cleared."}).json()
    assert alert["id"]

    # 11. A student associated with ISC receives the alert (device dev-a1 -> ISC).
    mine = client.get("/api/alerts/mine", headers=student_headers(10)).json()
    assert any(a["id"] == alert["id"] for a in mine)

    # And a student elsewhere (library, dev-e5 / user 14) does NOT get a building alert.
    other = client.get("/api/alerts/mine", headers=student_headers(14)).json()
    assert not any(a["id"] == alert["id"] for a in other)


def test_reset_clears_data_and_restores_safe_defaults(client):
    import asyncio
    from app import scenario

    # Create some state: a report, an incident, an alert, and a cleared zone.
    _submit(client, 10, "saw", 6, 2, "smoke")
    inc = client.post("/api/incidents", headers=sec_headers(),
                      json={"title": "ISC"}).json()
    client.post(f"/api/incidents/{inc['id']}/field-observations", headers=sec_headers(),
                json={"officer_id": "OFC-1", "building_id": 6, "floor": 2,
                      "findings": "checking"})
    client.post("/api/alerts", headers=sec_headers(),
                json={"scope": "building", "building_id": 6, "message": "Avoid ISC."})
    zones = client.get("/api/zones", headers=sec_headers()).json()
    isc = next(z for z in zones if z["building_id"] == 6 and z["floor"] == 2)
    client.post(f"/api/zones/{isc['zone_id']}/status", headers=sec_headers(),
                json={"security_status": "cleared"})

    # Sanity: data exists.
    assert len(client.get("/api/reports", headers=sec_headers()).json()) >= 1
    assert len(client.get("/api/incidents", headers=sec_headers()).json()) >= 1
    assert len(client.get("/api/alerts", headers=sec_headers()).json()) >= 1

    # Reset.
    asyncio.get_event_loop().run_until_complete(scenario.reset())

    # All transactional data is gone.
    assert client.get("/api/reports", headers=sec_headers()).json() == []
    assert client.get("/api/incidents", headers=sec_headers()).json() == []
    assert client.get("/api/alerts", headers=sec_headers()).json() == []

    # Every zone is back to safe defaults — never left 'cleared' by the reset.
    zones_after = client.get("/api/zones", headers=sec_headers()).json()
    for z in zones_after:
        assert z["security_status"] == "unassessed"
        assert z["system_assessment"] == "insufficient_information"
