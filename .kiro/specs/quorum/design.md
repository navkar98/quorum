# Quorum — Design

## Overview

A single FastAPI backend over SQLite, a React/Vite/TypeScript frontend hosting both the
student (mobile-first) and security (desktop-first) apps, Server-Sent Events for live
updates, and a modular AI layer that defaults to deterministic rules. All Wi-Fi data and
notifications are simulated.

> Schema note: the project references `db/schema.sql` as "provided." No schema file was
> present in the workspace at start, so this design defines `db/schema.sql` and it becomes
> the authoritative schema. Per the project rules it must not be changed without approval.

## Architecture

```
            ┌─────────────────────────────────────────────┐
            │                React + Vite                  │
            │  Student app (mobile)   Security app (desktop)│
            └───────────────┬───────────────┬──────────────┘
                   REST/JSON │               │ REST/JSON + SSE
            ┌───────────────▼───────────────▼──────────────┐
            │                 FastAPI backend               │
            │  auth (role) │ routers │ events(SSE) │ scenario│
            │  evidence engine (deterministic)              │
            │  AIProvider (rules default | optional llm)    │
            └───────────────┬───────────────────────────────┘
                            │ sqlite3
                     ┌──────▼──────┐
                     │  SQLite DB  │  schema.sql + seed JSON
                     └─────────────┘
```

- **Async AI:** report POST writes the row, publishes a `report.created` event, and
  schedules analysis as a FastAPI background task. When analysis finishes it writes an
  `analysis` row and publishes `analysis.updated`.
- **Auth:** demo-grade bearer tokens map to a role (`student` or `security`) and an actor
  id. A dependency `require_security` guards all privileged routes. Student tokens also
  carry a `device_id` used for Wi-Fi association and report isolation.

## Database schema (db/schema.sql)

SQLite. Enums enforced via CHECK constraints. Device identities live only in
`wifi_association`, which is never exposed by security APIs.

- `building(id, name, floors)` — the 10 UMass Boston buildings; floor counts from seed.
- `zone(id, building_id, floor)` — floor-level zones; `floor` NULL = whole building.
- `app_user(id, role, display_name, device_id)` — demo users; `role ∈ {student,security}`.
- `report(id, reporter_user_id, device_id, observation_type, building_id, floor,
  description, photo_path, created_at, incident_id, source_confidence)` —
  `observation_type ∈ {saw,heard,was_told}`. `device_id` used for distinct-source logic;
  never returned to security as an identity (reports are shown without reporter identity).
- `report_analysis(id, report_id, kind, summary, distress_indicators, hazards,
  contradiction_flag, duplicate_flag, source_refs, created_at)` — `kind ∈ {ai,rules}`.
- `incident(id, title, status, created_by, created_at)` —
  `status ∈ {open,monitoring,closed}` (dispatch workflow state, not a safety verdict).
- `field_observation(id, incident_id, officer_id, building_id, floor, findings,
  observed_at, created_at)` — radio observations entered by dispatchers.
- `zone_assessment(id, zone_id, system_assessment, security_status, updated_by,
  updated_at)` — current per-zone state. `system_assessment ∈ {potential_impact,
  conflicting_evidence,insufficient_information}`; `security_status ∈ {unassessed,
  under_investigation,restricted,cleared}`. Default security_status = `unassessed`.
- `zone_status_history(id, zone_id, old_status, new_status, changed_by, changed_at,
  note)` — audit of security-status changes.
- `wifi_association(id, device_id, zone_id, confidence, observed_at, stale)` —
  simulated device↔zone links. BACKEND ONLY. Never in security responses.
- `feedback_request(id, zone_id, building_id, floor, question, created_by, created_at)`.
- `feedback_response(id, request_id, device_id, answer, created_at)` —
  `answer ∈ {yes,no,unsure}`. Tallied only; identities never exposed.
- `alert(id, scope, building_id, floor, message, approved_by, approved_at)` —
  `scope ∈ {campus,building,floor}`. Existence of a row = approved+sent.
- `alert_audit(id, alert_id, actor_id, action, detail, at)` — approval audit trail.

Indexes on `report(building_id,created_at)`, `wifi_association(zone_id)`,
`zone_assessment(zone_id)`.

## API design

All under `/api`. Student routes require a student token; privileged routes require
`require_security`.

Student / shared:
- `POST /api/reports` (student) — create report; returns id immediately. Fires async
  analysis.
- `GET  /api/wifi/suggest` (student) — suggested building/floor + confidence/staleness
  for the caller's device.
- `GET  /api/feedback/mine` (student) — open feedback requests for the device's zone.
- `POST /api/feedback/{id}/respond` (student) — submit yes/no/unsure.
- `GET  /api/alerts/mine` (student) — alerts targeting the device's zone or campus.

Security:
- `GET  /api/reports` — list reports (no reporter identity fields).
- `GET  /api/incidents`, `POST /api/incidents`, `POST /api/incidents/{id}/attach`.
- `POST /api/incidents/{id}/field-observations`.
- `GET  /api/zones`, `GET /api/zones/{id}` — full zone picture (aggregate counts only).
- `POST /api/zones/{id}/status` — change security status; writes history + audit.
- `GET  /api/heatmap/incident`, `GET /api/heatmap/crowd` — the two separate heatmaps.
- `POST /api/feedback` — create targeted request; returns eligible device count.
- `GET  /api/feedback/{id}/results` — tallies only.
- `GET  /api/alerts/preview` — audience size for a scope. `POST /api/alerts` — approve+send.
- `GET  /api/alerts` — history.
- `GET  /api/events` — SSE stream of dashboard events.
- `POST /api/scenario/start`, `/stop`, `GET /api/scenario/status` — demo control.

Security responses are built by whitelisting fields — device_id and reporter identity are
never serialized into security payloads.

## Evidence correlation engine (deterministic)

Pure function over current DB state → per-zone assessment + cluster/flag annotations.

- **Grouping:** reports within the same building and a sliding time window (e.g. 15 min)
  form a candidate cluster, refined by floor.
- **Distinct-source corroboration:** corroboration strength = number of *distinct*
  `device_id`s, weighted by observation type (saw > heard > was_told). Repeated reports
  from the same device add detail but do not raise the distinct-source count. This is the
  core anti-inflation invariant.
- **Contradictions:** opposing findings for the same zone/time (e.g. a "saw smoke" report
  vs a field observation of "no smoke") set `conflicting_evidence`.
- **Duplicates:** near-identical reports from the same device/time flagged as duplicate.
- **System assessment mapping:**
  - `potential_impact` when ≥2 distinct firsthand-leaning sources or a corroborating
    field observation.
  - `conflicting_evidence` when credible opposing evidence exists.
  - `insufficient_information` otherwise (and as the default — never "safe").
- The engine returns suggested zones to review. It never sets security status and never
  declares real/fake/resolved. Recomputed on each relevant event.

## AI layer

```
class AIProvider(Protocol):
    def analyze_report(self, text, image_path) -> Analysis  # summary, distress,
        # hazards, extracted observations, uncertainty/contradiction notes, source_refs
```

- `RulesProvider` (default): keyword/heuristic summary, distress lexicon, hazard lexicon,
  image = "image attached (not analyzed)". Always available; output `kind="rules"`.
- `LLMProvider` (optional): used only if an API key env var is set; wrapped with a
  timeout. On any error/timeout the service falls back to `RulesProvider` and labels
  output `kind="rules"`.
- The service treats all input as untrusted (no eval, no execution, size limits, image
  never used for face/identity).

> Kiro CLI check: before relying on Kiro CLI for headless text/image analysis, verify
> support. Default path does not depend on it; `RulesProvider` guarantees the demo works
> offline. `LLMProvider` is the modular opt-in.

## Realtime (SSE)

`events.py` holds an in-process async pub/sub. Handlers publish typed events
(`report.created`, `analysis.updated`, `zone.updated`, `feedback.created`,
`alert.created`). `GET /api/events` streams them to the security dashboard; the student
app polls `*/mine` endpoints (simple + robust for mobile).

## Frontend

- **Student (mobile-first):** bottom tab bar Report / Feedback / Response. Large touch
  targets, high contrast, no sound/vibration. Report form uses `GET /wifi/suggest` to
  prefill, editable.
- **Security (desktop-first):** left nav Dashboard / Incidents / Zones / Feedback /
  Alerts. Dashboard hosts the campus map (simple SVG grid approximating layout) with a
  toggle between the two heatmaps, plus live feeds via SSE. AI content rendered in clearly
  labeled "AI / rules" panels, visually separated from raw observations and field reports.

## Testing

`pytest` + `hypothesis`:
- Property: distinct-source corroboration never increases from repeated same-device
  reports (#9,#10).
- Access: student token cannot read others' reports (#1); security payloads contain no
  device_id/identity (#2,#3).
- Authz: non-security role rejected on zone status + alert approval (#5,#6).
- Defaults: new zone assessment defaults to `unassessed`/`insufficient_information`, never
  cleared/safe (#12); negative field observation does not flip a building to cleared
  (#13).
- AI: fallback labels output as `rules`; AI cannot set security status or approve alerts
  (#7).
- Alert audit row always written on approval (#6).
