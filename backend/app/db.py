"""SQLite connection management and schema bootstrap."""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Iterator

from . import config


def now_iso() -> str:
    """UTC timestamp in ISO 8601."""
    return datetime.now(timezone.utc).isoformat()


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(config.DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def get_conn() -> Iterator[sqlite3.Connection]:
    conn = connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_schema() -> None:
    """Create tables from the authoritative schema file if needed."""
    sql = config.SCHEMA_PATH.read_text(encoding="utf-8")
    with get_conn() as conn:
        conn.executescript(sql)


def has_data() -> bool:
    with get_conn() as conn:
        row = conn.execute("SELECT COUNT(*) AS n FROM building").fetchone()
        return bool(row and row["n"] > 0)
