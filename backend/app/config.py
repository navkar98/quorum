"""Central configuration and paths."""
from __future__ import annotations

import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BACKEND_DIR.parent
DB_DIR = REPO_ROOT / "db"
SCHEMA_PATH = DB_DIR / "schema.sql"
SEED_DIR = DB_DIR / "seed"

# Database file (overridable for tests).
DB_PATH = Path(os.environ.get("QUORUM_DB", str(BACKEND_DIR / "quorum.db")))

# Uploaded photos (treated as untrusted; never served to students).
UPLOAD_DIR = Path(os.environ.get("QUORUM_UPLOADS", str(BACKEND_DIR / "uploads")))

# Optional LLM provider. If unset, the deterministic RulesProvider is always used.
LLM_API_KEY = os.environ.get("QUORUM_LLM_API_KEY", "")
LLM_TIMEOUT_SEC = float(os.environ.get("QUORUM_LLM_TIMEOUT", "8"))

# Clustering window for the evidence engine.
CLUSTER_WINDOW_MIN = int(os.environ.get("QUORUM_CLUSTER_WINDOW_MIN", "20"))

# Crowd-density freshness window (minutes) for "fresh" vs stale associations.
WIFI_FRESH_MIN = int(os.environ.get("QUORUM_WIFI_FRESH_MIN", "15"))
