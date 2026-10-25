# Quorum — Technical Steering

## Architecture

Simple, maintainable, monolithic. No microservices.

- **Backend:** Python + FastAPI. Single API service. Async endpoints so reports appear
  immediately; AI analysis runs asynchronously in the background.
- **Database:** SQLite (file-based, zero-setup) using the schema in `db/schema.sql`.
  Access via a thin data layer. The schema is authoritative — **do not modify it
  without explicit approval**.
- **Frontend:** React + Vite + TypeScript. Two apps built from one codebase:
  - Student app (mobile-first, three tabs: Report / Feedback / Response).
  - Security console (desktop-first dashboard).
- **Realtime:** Server-Sent Events (SSE) for near-real-time dashboard updates. Simple,
  one-directional, demo-friendly.
- **AI:** Modular `AIProvider` interface. Default to a deterministic rules-based
  provider so the demo always works offline. An optional LLM provider can be swapped in
  via env var. If AI is unavailable or times out, fall back to deterministic rules and
  label results as `rules` rather than `ai`.

## Project layout

```
quorum/
  db/
    schema.sql           # authoritative schema (do not change without approval)
    seed/                # synthetic JSON data files
  backend/
    app/
      main.py
      db.py              # connection + schema bootstrap
      auth.py            # role-based access (student vs security)
      models.py          # pydantic schemas
      routers/           # reports, incidents, zones, wifi, feedback, alerts, scenario
      ai/                # AIProvider interface + rules + optional llm
      evidence.py        # evidence correlation engine (deterministic)
      events.py          # SSE pub/sub
      seed.py            # seed loader
      scenario.py        # synthetic scenario replay
    tests/               # safety-invariant + property-based tests
  frontend/
    src/
      student/
      security/
      shared/
```

## Conventions

- Backend: type-hinted Python, pydantic models, dependency-injected auth.
- Enforce every permission and approval in backend code, not only in the UI.
- Tests use `pytest` + `hypothesis` for property-based safety invariants.
- Keep the AI interface behind one module so it is swappable and testable.

## Commands

- Backend install: `pip install -r backend/requirements.txt`
- Backend run: `uvicorn app.main:app --reload` from `backend/`
- Seed DB: `python -m app.seed` from `backend/`
- Tests: `pytest` from `backend/`
- Frontend install: `npm install` in `frontend/`
- Frontend dev: `npm run dev` in `frontend/`

## Non-negotiable technical guardrails

- Student reports are visible only to security; students never see others' reports or
  identities.
- Security dashboard APIs never expose individual device identities or movement
  histories — only aggregate counts. Device-to-zone associations are backend-only.
- No student-facing alert/feedback goes out without an authenticated security action.
- Only security roles can change official zone status; enforced server-side.
- Repeated reports from one device must not inflate corroboration.
- Unassessed zones are never auto-labeled safe. A negative field observation never
  auto-clears a whole building.
- Maintain audit records for official security decisions.
- Do not log report contents or device identifiers unnecessarily.
