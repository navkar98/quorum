"""Test fixtures. Each test run uses a fresh temp DB so state is isolated."""
from __future__ import annotations

import importlib
import os
import tempfile
from pathlib import Path

import pytest


@pytest.fixture()
def client(monkeypatch):
    tmp = Path(tempfile.mkdtemp())
    db_path = tmp / "test_quorum.db"
    monkeypatch.setenv("QUORUM_DB", str(db_path))
    monkeypatch.setenv("QUORUM_UPLOADS", str(tmp / "uploads"))
    # Reload config + db so they pick up the env.
    from app import config as config_mod
    importlib.reload(config_mod)
    from app import db as db_mod
    importlib.reload(db_mod)

    db_mod.init_schema()
    from app import seed as seed_mod
    importlib.reload(seed_mod)
    seed_mod.seed()

    # Import app AFTER env is set.
    from fastapi.testclient import TestClient
    from app import main as main_mod
    importlib.reload(main_mod)
    with TestClient(main_mod.app) as c:
        yield c


def sec_headers():
    return {"Authorization": "Bearer quorum-1"}


def student_headers(user_id: int = 10):
    return {"Authorization": f"Bearer quorum-{user_id}"}
