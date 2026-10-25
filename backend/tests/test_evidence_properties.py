"""Property-based tests for the evidence engine's core safety invariant:

No matter how many times a single device reports, the distinct-source count equals the
number of unique devices, and repeated same-device reports can never, on their own, push
a zone to 'potential_impact'. This is the anti-inflation guarantee (safety #9, #10).

These tests exercise the engine directly against a fresh in-memory-style DB per example
so each generated example is fully isolated (no shared-fixture accumulation).
"""
from __future__ import annotations

import importlib
import os
import tempfile
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

DEVICES = ["dev-a1", "dev-b2", "dev-c3", "dev-d4", "dev-e5", "dev-f6"]


def _fresh_engine(tmpdir: Path):
    """Point config/db at a fresh DB file and return (db, evidence) modules seeded."""
    os.environ["QUORUM_DB"] = str(tmpdir / "prop.db")
    from app import config as config_mod
    importlib.reload(config_mod)
    from app import db as db_mod
    importlib.reload(db_mod)
    db_mod.init_schema()
    from app import seed as seed_mod
    importlib.reload(seed_mod)
    seed_mod.seed()
    from app import evidence as ev_mod
    importlib.reload(ev_mod)
    return db_mod, ev_mod


def _insert_report(db_mod, device_id: str):
    with db_mod.get_conn() as conn:
        conn.execute(
            "INSERT INTO report(reporter_user_id, device_id, observation_type, "
            "building_id, floor, description, created_at) VALUES (?,?,?,?,?,?,?)",
            (None, device_id, "saw", 6, 2, "smoke", db_mod.now_iso()),
        )


@settings(max_examples=40, deadline=None)
@given(report_devices=st.lists(st.integers(min_value=0, max_value=5),
                               min_size=1, max_size=20))
def test_distinct_sources_equals_unique_devices(report_devices):
    tmp = Path(tempfile.mkdtemp())
    db_mod, ev_mod = _fresh_engine(tmp)

    for idx in report_devices:
        _insert_report(db_mod, DEVICES[idx])

    clusters = ev_mod.correlate()
    cell = next(c for c in clusters if c.building_id == 6 and c.floor == 2)

    unique_devices = len(set(report_devices))
    assert len(cell.report_ids) == len(report_devices)
    # Anti-inflation: distinct sources never exceeds the unique device count.
    assert cell.distinct_sources == unique_devices
    # A single repeating device can never reach potential_impact on its own.
    if unique_devices < 2:
        assert cell.system_assessment != "potential_impact"
