# Quorum — Implementation Tasks

- [x] 1. Database schema and seed data
  - [x] 1.1 Author `db/schema.sql` with all tables, enums (CHECK), indexes (Req 13.1)
  - [x] 1.2 Create synthetic seed JSON: buildings/floors, zones, users, wifi
    associations, a scenario timeline of reports/feedback/field observations
    (Req 13.3, 14)
- [x] 2. Backend foundation
  - [x] 2.1 FastAPI app, config, SQLite connection + schema bootstrap (Req 13)
  - [x] 2.2 Pydantic models with security-safe serializers (whitelist fields) (Req 5,7)
  - [x] 2.3 Role-based auth: student/security tokens, `require_security` dependency,
    device_id on student tokens (Req 13.2, safety 1-6)
  - [x] 2.4 Seed loader `app.seed` (Req 13.3)
  - [x] 2.5 SSE event bus `events.py` + `GET /api/events` (Req 5.6, 13.4)
- [x] 3. Wi-Fi zone identification (simulated)
  - [x] 3.1 Suggestion service: device → building/floor + confidence/staleness (Req 4.1,4.2)
  - [x] 3.2 Aggregate per-zone device counts with freshness; backend-only associations
    (Req 4.3, 4.4, safety 2-3)
- [x] 4. Student APIs
  - [x] 4.1 `POST /reports` immediate ack + async analysis trigger (Req 1, 12.2)
  - [x] 4.2 `GET /wifi/suggest`, `GET /feedback/mine`, `POST /feedback/{id}/respond`,
    `GET /alerts/mine` with report isolation (Req 1.5, 2, 3)
- [x] 5. Evidence correlation engine
  - [x] 5.1 Grouping + clusters + suggested zones (Req 11.1,11.2)
  - [x] 5.2 Distinct-source corroboration, duplicate + contradiction flags, firsthand vs
    hearsay (Req 11.3,11.4, safety 9-11)
  - [x] 5.3 System-assessment mapping with insufficient-info default (Req 8.2, safety 12-14)
- [x] 6. AI layer (modular + fallback)
  - [x] 6.1 `AIProvider` interface + `RulesProvider` default (Req 12.1,12.3)
  - [x] 6.2 Optional `LLMProvider` with timeout + fallback labeling; untrusted-input
    handling (Req 12.3,12.5, safety 7-8,18)
- [x] 7. Security APIs
  - [x] 7.1 Reports list, incidents CRUD + attach + field observations (Req 6)
  - [x] 7.2 Zones: full picture + status change with history + audit (Req 8, safety 5,14)
  - [x] 7.3 Two heatmaps: incident activity + crowd density (Req 5.2,5.3,5.4)
  - [x] 7.4 Targeted feedback: create (eligible count) + tally results (Req 9, safety 4)
  - [x] 7.5 Alerts: preview audience, approve+send with audit, history (Req 10, safety 4,6)
- [x] 8. Scenario simulator
  - [x] 8.1 Chronological replay publishing live events; start/stop/status (Req 14)
- [x] 9. Frontend — student (mobile-first)
  - [x] 9.1 App shell + tab bar; accessible, discreet styling (Req 1.1,1.6)
  - [x] 9.2 Report tab with Wi-Fi prefill + manual override + optional photo (Req 1)
  - [x] 9.3 Feedback tab (yes/no/unsure) (Req 2)
  - [x] 9.4 Response tab (alerts with source + time) (Req 3)
- [x] 10. Frontend — security (desktop-first)
  - [x] 10.1 App shell + nav + SSE live wiring (Req 5.6)
  - [x] 10.2 Dashboard: campus map + two-mode heatmap toggle + live feeds (Req 5)
  - [x] 10.3 Incidents: create/review, attach reports, field observations, AI panel
    (Req 6,7)
  - [x] 10.4 Zones: full picture + status control + history (Req 8)
  - [x] 10.5 Feedback + Alerts consoles with audience preview (Req 9,10)
- [x] 11. Safety tests (pytest + hypothesis)
  - [x] 11.1 Distinct-source corroboration property (safety 9-11)
  - [x] 11.2 Report isolation + aggregate-only Wi-Fi exposure (safety 1-3)
  - [x] 11.3 Security-only status + alert authorization + audit (safety 4-6)
  - [x] 11.4 AI non-authority + default-not-safe (safety 7,12-13)
  - [x] 11.5 Full end-to-end demo-flow integration test (Req 14.3)
- [x] 12. Dev hooks + docs
  - [x] 12.1 Kiro hook: run safety tests on backend file save
  - [x] 12.2 README with run instructions + demo script
