# Quorum

Quorum helps campuses respond faster and more safely during emergencies. It turns what
people on the ground are seeing into a clear, shared picture for campus security, so they
can make better decisions and send trusted guidance to the people who need it.

Quorum is an AI-assisted campus emergency coordination prototype for UMass Boston. Students
submit observations; AI and deterministic rules organize incoming information, surface
potential incident clusters, and highlight conflicting evidence. **Campus security keeps
full authority** over official incident statuses, affected zones, feedback requests, and
alerts. Quorum supplements — it never replaces — existing emergency communication.

> Hackathon prototype. All Wi-Fi data and notifications are **simulated**. It never connects
> to real university emergency infrastructure and must never delay existing response
> procedures.

## What's inside

| Area | Stack |
|------|-------|
| Backend API | Python + FastAPI + SQLite, Server-Sent Events for live updates |
| Student app | React + Vite + TypeScript, mobile-first (Report / Feedback / Response) |
| Security console | React + Vite + TypeScript, desktop-first (Dashboard / Incidents / Zones / Feedback / Alerts) |
| Evidence engine | Deterministic correlation with distinct-source corroboration |
| AI layer | Modular `AIProvider` — deterministic rules by default, optional LLM, always falls back safely |
| Specs | `.kiro/specs/quorum` (requirements, design, tasks) and `.kiro/steering` (product, tech, safety) |

## Two heatmaps, kept conceptually separate

- **Incident activity** — concentration of recent student reports. Report density does
  *not* prove danger.
- **Crowd density** — estimated Wi-Fi-connected device counts (aggregate only, no
  identities). Device counts are *not* exact occupancy and do *not* prove safety.

## Prerequisites

- Python 3.9+ (tested on 3.9)
- Node.js 18+ and npm

## Run it

### 1. Backend

```powershell
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8099
```

The database is created and seeded automatically on first start. To reseed from scratch:

```powershell
cd backend
python -m app.seed --reset
```

### 2. Frontend

```powershell
cd frontend
npm install
npm run dev
```

Open the printed URL (default http://localhost:5173). Vite proxies `/api` to the backend
on port 8099.

- **Student app:** `/student`  (open on a phone on the same network via the Vite network URL)
- **Security console:** `/security`

### 3. Tests

```powershell
cd backend
python -m pytest -q
```

Includes safety-invariant tests, a property-based anti-inflation test, and a full
end-to-end demo-flow test.

## Demo script (≈3 minutes)

1. Open the **Security console** at `/security`, sign in as a dispatcher. Open the
   **Dashboard**.
2. In the left sidebar, click **Start scenario**. Synthetic reports begin arriving.
3. Watch the **Incident activity** heatmap: the Integrated Sciences Complex (ISC) lights up
   as distinct students report smoke. Toggle to **Crowd density** to show it's a different,
   separate signal.
4. Note the "Attention: clusters & conflicts" panel: ISC shows **Potential impact** with
   the distinct-source count — and repeated reports from the same device do *not* inflate
   it.
5. Go to **Incidents**, create "ISC possible smoke", attach the ISC reports, and enter a
   **field observation** (officer OFC-204, building 6, floor 2: "light haze from a hotplate,
   no active fire"). The assessment flips to **Conflicting evidence**.
6. Go to **Zones**, select ISC floor 2, and manually set the official status to **Under
   investigation**. Show the audit history.
7. Go to **Targeted Feedback**, pick ISC, ask "Did you personally observe smoke?" — note the
   eligible device count. Answer from the student app's **Feedback** tab.
8. Go to **Alerts**, scope **Building → ISC**, preview the audience, and **Approve & send**
   "Avoid the Integrated Sciences Complex until cleared."
9. On a phone (or second browser) in the **Student app**, open the **Response** tab: the
   ISC-associated student receives the alert; a student in the library does not.

You can submit a live report from a real phone at any time while the scenario runs.

## Safety guarantees (enforced server-side, covered by tests)

- Student reports go only to security; students never see others' reports or identities.
- Security dashboard APIs expose only aggregate Wi-Fi counts — never device identities or
  movement histories.
- Only security can change official zone status; every change is audited.
- Every alert requires authenticated security approval and writes an audit record. No AI
  output or student report can send an alert on its own.
- Repeated reports from one device never create independent corroboration.
- Unassessed zones are never auto-labeled safe; a negative field observation never
  auto-clears a building.
- If AI is unavailable, deterministic rules run and results are labeled accordingly.

See `.kiro/steering/safety.md` for the full list and `backend/tests/` for the tests that
enforce them.
