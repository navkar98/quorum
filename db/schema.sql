-- Quorum database schema (SQLite)
-- Authoritative schema. Do not modify without approval.
-- Device identities live only in wifi_association and report.device_id and are
-- never exposed through security-facing APIs.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS building (
    id      INTEGER PRIMARY KEY,
    name    TEXT NOT NULL UNIQUE,
    floors  INTEGER NOT NULL CHECK (floors >= 1)
);

CREATE TABLE IF NOT EXISTS zone (
    id          INTEGER PRIMARY KEY,
    building_id INTEGER NOT NULL REFERENCES building(id),
    floor       INTEGER,            -- NULL = whole-building zone
    UNIQUE (building_id, floor)
);

CREATE TABLE IF NOT EXISTS app_user (
    id           INTEGER PRIMARY KEY,
    role         TEXT NOT NULL CHECK (role IN ('student','security')),
    display_name TEXT NOT NULL,
    device_id    TEXT                -- students carry a simulated device id
);

CREATE TABLE IF NOT EXISTS report (
    id               INTEGER PRIMARY KEY,
    reporter_user_id INTEGER REFERENCES app_user(id),
    device_id        TEXT,           -- simulated source device; backend-only
    observation_type TEXT NOT NULL CHECK (observation_type IN ('saw','heard','was_told')),
    building_id      INTEGER NOT NULL REFERENCES building(id),
    floor            INTEGER,
    description      TEXT,
    photo_path       TEXT,
    source_confidence REAL DEFAULT 0.5,
    incident_id      INTEGER REFERENCES incident(id),
    created_at       TEXT NOT NULL   -- ISO 8601 UTC
);

CREATE TABLE IF NOT EXISTS report_analysis (
    id                  INTEGER PRIMARY KEY,
    report_id           INTEGER NOT NULL REFERENCES report(id),
    kind                TEXT NOT NULL CHECK (kind IN ('ai','rules')),
    summary             TEXT,
    distress_indicators TEXT,        -- JSON array
    hazards             TEXT,        -- JSON array
    contradiction_flag  INTEGER NOT NULL DEFAULT 0,
    duplicate_flag      INTEGER NOT NULL DEFAULT 0,
    source_refs         TEXT,        -- JSON array of report ids / evidence
    created_at          TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS incident (
    id         INTEGER PRIMARY KEY,
    title      TEXT NOT NULL,
    status     TEXT NOT NULL DEFAULT 'open'
                   CHECK (status IN ('open','monitoring','closed')),
    created_by INTEGER REFERENCES app_user(id),
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS field_observation (
    id          INTEGER PRIMARY KEY,
    incident_id INTEGER REFERENCES incident(id),
    officer_id  TEXT NOT NULL,
    building_id INTEGER NOT NULL REFERENCES building(id),
    floor       INTEGER,
    findings    TEXT NOT NULL,
    observed_at TEXT NOT NULL,
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS zone_assessment (
    id                INTEGER PRIMARY KEY,
    zone_id           INTEGER NOT NULL UNIQUE REFERENCES zone(id),
    system_assessment TEXT NOT NULL DEFAULT 'insufficient_information'
        CHECK (system_assessment IN
            ('potential_impact','conflicting_evidence','insufficient_information')),
    security_status   TEXT NOT NULL DEFAULT 'unassessed'
        CHECK (security_status IN
            ('unassessed','under_investigation','restricted','cleared')),
    updated_by        INTEGER REFERENCES app_user(id),
    updated_at        TEXT
);

CREATE TABLE IF NOT EXISTS zone_status_history (
    id         INTEGER PRIMARY KEY,
    zone_id    INTEGER NOT NULL REFERENCES zone(id),
    old_status TEXT,
    new_status TEXT NOT NULL,
    changed_by INTEGER REFERENCES app_user(id),
    changed_at TEXT NOT NULL,
    note       TEXT
);

-- BACKEND ONLY. Never exposed by security-facing endpoints.
CREATE TABLE IF NOT EXISTS wifi_association (
    id          INTEGER PRIMARY KEY,
    device_id   TEXT NOT NULL,
    zone_id     INTEGER NOT NULL REFERENCES zone(id),
    confidence  REAL NOT NULL DEFAULT 0.5,
    observed_at TEXT NOT NULL,
    stale       INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS feedback_request (
    id          INTEGER PRIMARY KEY,
    zone_id     INTEGER REFERENCES zone(id),
    building_id INTEGER REFERENCES building(id),
    floor       INTEGER,
    question    TEXT NOT NULL,
    created_by  INTEGER REFERENCES app_user(id),
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS feedback_response (
    id         INTEGER PRIMARY KEY,
    request_id INTEGER NOT NULL REFERENCES feedback_request(id),
    device_id  TEXT,                 -- backend-only; never tallied with identity
    answer     TEXT NOT NULL CHECK (answer IN ('yes','no','unsure')),
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS alert (
    id          INTEGER PRIMARY KEY,
    scope       TEXT NOT NULL CHECK (scope IN ('campus','building','floor')),
    building_id INTEGER REFERENCES building(id),
    floor       INTEGER,
    message     TEXT NOT NULL,
    approved_by INTEGER NOT NULL REFERENCES app_user(id),
    approved_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS alert_audit (
    id       INTEGER PRIMARY KEY,
    alert_id INTEGER REFERENCES alert(id),
    actor_id INTEGER NOT NULL REFERENCES app_user(id),
    action   TEXT NOT NULL,
    detail   TEXT,
    at       TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_report_building_time ON report(building_id, created_at);
CREATE INDEX IF NOT EXISTS idx_wifi_zone ON wifi_association(zone_id);
CREATE INDEX IF NOT EXISTS idx_wifi_device ON wifi_association(device_id);
CREATE INDEX IF NOT EXISTS idx_assessment_zone ON zone_assessment(zone_id);
CREATE INDEX IF NOT EXISTS idx_feedback_resp_req ON feedback_response(request_id);
