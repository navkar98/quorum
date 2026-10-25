# Quorum — Screen-by-Screen Guide

This document explains every screen in Quorum and what it does. Quorum has two
front-ends built from one codebase:

- **Student app** — mobile-first, three tabs (Report, Feedback, Alerts).
- **Security console** — desktop-first dashboard (Dashboard, Incidents, Zones, Targeted
  Feedback, Alerts).

All Wi-Fi data and notifications are **simulated**. The app supplements — never replaces —
official campus emergency communication.

A note on "AI": incoming reports are analyzed by a deterministic **rules** engine
(keyword/lexicon matching), labeled "Rules analysis" in the UI. No AI model runs by
default, and no AI ever writes or sends an alert or changes an official status. An optional
LLM provider can be enabled later behind an env var without changing these guarantees.

---

## Entry / Landing

**Route:** `/`

A simple chooser with two cards:

- **Student app** → `/student`
- **Security console** → `/security`

Also shows the simulation disclaimer: in a real emergency, follow official instructions
and call 911.

<!--IMG:Screenshot 2026-10-24 182447.png|Landing screen: choose the student app or the security console.-->


---

# Student app (mobile-first)

**Route:** `/student`

## Student sign-in

The first screen if you have no student session. Lists the seeded demo students. Under each
name it shows that student's **estimated location** (building + floor) derived from
simulated campus Wi-Fi — e.g. "📍 Integrated Sciences Complex, floor 2". If Wi-Fi is weak
or stale it appends "(uncertain)"; if there's no association it reads "Location
unavailable". Tapping a student signs in as them.

> Why location is shown here: it is the student's *own* suggested location (the same value
> they'd see after signing in), used so you can pick a student in a specific zone to test
> targeting. It is never another person's data.

After sign-in, a bottom tab bar shows **Report · Feedback · Alerts**, and the header shows a
small live-connection dot (green = push stream connected). Feedback and Alerts tabs show a
small red dot when a new item has arrived for a tab you aren't currently viewing.

<!--IMG:Screenshot 2026-10-24 182548.png|Student sign-in: each demo student shows their estimated Wi-Fi location.-->


## Tab 1 — Report

Where a student reports what they observed. Controls, top to bottom:

1. **Observation type** (large buttons): *I saw it* (firsthand), *I heard it*, *I was told*
   (hearsay). Exactly one is required. This distinction matters: firsthand is weighted above
   hearsay in the evidence engine.
2. **Suggested location banner** — pre-fills building/floor from the student's simulated
   Wi-Fi. If Wi-Fi is unavailable/uncertain it asks the student to pick manually.
3. **Building** (dropdown) and **Floor** (optional dropdown) — always editable, so the
   student can override the Wi-Fi guess.
4. **Description** (optional, up to 2000 chars).
5. **Photo** (optional; jpg/png/webp).
6. **Submit report** — acknowledges immediately. Analysis runs asynchronously in the
   background, so submission is never blocked.

A confirmation toast appears on success. A reminder states the report goes only to campus
security and is never shared with other students.

<!--IMG:Screenshot 2026-10-24 182631.png|Report tab: observation type, Wi-Fi-suggested location (editable), description, and photo.-->


## Tab 2 — Feedback

Shows neutral questions security has sent to the student's current zone (e.g. "Did you
personally observe smoke in your building?"). The student answers **Yes / No / Unsure**.
After answering, the card confirms the choice. New questions appear instantly via push (and
a slow poll as a fallback). A note clarifies that an answer helps assessment but does not by
itself confirm or dismiss an incident.

<!--IMG:Screenshot 2026-10-24 182702.png|Feedback tab: security's neutral questions, answered Yes / No / Unsure (shown here with none pending).-->


## Tab 3 — Alerts (page heading: "Official guidance")

Shows short, security-approved instructions relevant to the student — campus-wide alerts,
plus alerts for their building/floor. Each alert displays:

- The message (e.g. "Avoid the Integrated Sciences Complex until cleared.")
- The official source and dispatcher (e.g. "Campus Security · Dispatcher A")
- The scope (Campus-wide / building / building + floor)
- The issuance time

New alerts arrive instantly via push. The tab intentionally shows **no** unverified incident
details, rumor counts, distress scores, or other students' locations — only approved
guidance. A footer reminds users to follow official instructions and call 911 in an
emergency.

<!--IMG:Screenshot 2026-10-24 182747.png|Alerts tab: an approved alert with its source, scope, and issuance time.-->


---

# Security console (desktop-first)

**Route:** `/security`

## Security sign-in

Lists the seeded dispatcher accounts; selecting one signs in. All privileged actions are
enforced server-side by role, not just hidden in the UI.

<!--IMG:Screenshot 2026-10-24 183711.png|Security sign-in: pick a dispatcher account.-->


## Persistent sidebar (all screens)

- **Live status** — a dot showing whether the dashboard's live (SSE) event stream is
  connected, plus the signed-in dispatcher's name.
- **Navigation** — Dashboard, Incidents, Zones, Targeted Feedback, Alerts.
- **Demo scenario controls:**
  - **Start scenario** — replays a synthetic timeline of reports and a field observation so
    the whole flow animates live.
  - **Stop** — stops new synthetic events (does not erase anything already created).
  - **Reset demo data** — clears all reports, incidents, field observations, feedback, and
    alerts, and returns every zone to **Unassessed / Insufficient information**. Keeps
    buildings, users, and Wi-Fi so you can run the demo again. Asks for confirmation;
    disabled while a scenario is running.
  - **Sign out.**

## Screen 1 — Dashboard

The situational overview. Contents:

- **Stat row:** active incidents, zones to review, recent report count.
- **Campus map** with a toggle between two intentionally separate heatmaps:
  - **Incident activity** — colors buildings by the system assessment derived from recent
    reports (red = potential impact, amber = conflicting evidence, slate = reports present).
    The number on each building is the recent report count. *Report density alone never
    proves danger.*
  - **Crowd density** — colors buildings by estimated Wi-Fi-connected device counts
    (aggregate only, no identities). *Device counts are not exact occupancy and do not prove
    safety.*
  - **Hover any building** to see a per-floor tooltip: devices per floor (⚠ if stale),
    reports per floor with the **distinct-source** count, and the per-floor system
    assessment, plus total devices and stale/unknown counts.
  - The map layout approximates the real UMass Boston waterfront campus (relative positions,
    not survey coordinates).
- **Live feed** — a running list of events (new report, analysis ready, zone updated, field
  observation, feedback, alert, scenario progress).
- **Attention: clusters & conflicts** — zones flagged as potential impact or conflicting,
  with distinct-source counts and contradiction/duplicate notes.

Everything refreshes in near-real-time as events arrive.

<!--IMG:Screenshot 2026-10-24 183300.png|Dashboard (Incident activity): campus map with ISC flagged, live feed, and the clusters/conflicts panel.-->


## Screen 2 — Incidents

Create and work incidents. Left column:

- **Create incident** — give it a title.
- **Incidents** — list; click to select one.
- **Unassigned reports** — check reports and **attach** them to the selected incident.

Right column (for the selected incident):

- **Enter field observation (radio)** — record a dispatcher-entered observation: officer ID,
  building, floor, findings. These are kept visually separate from student reports and from
  AI/rules output. Adding one re-runs the evidence engine (which may surface a
  contradiction).
- **Associated reports** — each shown as a card (see "Report card" below).

<!--IMG:Screenshot 2026-10-24 183502.png|Incidents: create an incident, pick from the list, and attach unassigned reports.-->


## Report card (used on Incidents and Zones)

For each report it shows the raw observation and the analysis, clearly separated:

- **Observation badge** (Saw / Heard / Was told), building/floor, time.
- **Description** and a "photo attached" chip if present. No reporter identity is ever shown.
- **Analysis panel** (tagged "Rules analysis" or "AI analysis"): summary, detected hazards,
  distress indicators, source references, and flags for **contradiction** and **possible
  duplicate**.

## Screen 3 — Zones

Per-zone picture and official status control. Left column: a table of zones showing system
assessment, security status, and estimated device count.

Right column (selected zone):

- **Header** with system assessment (automated, advisory) and **security status** (official,
  human-set) side by side, plus estimated device count with a staleness note.
- **Status controls** — set the official security status: **Unassessed / Under investigation
  / Restricted / Cleared**. Only security can do this; each change is written to an audit
  history with an optional note. (The system never auto-labels a zone safe, and a single
  negative field observation never auto-clears a building.)
- **Feedback tallies** — Yes/No/Unsure counts only; no respondent identities.
- **Field observations** for the zone.
- **Status history (audit)** — every official status change with time and note.
- **Alert history** for the zone.
- **Related reports** — report cards for the zone.

<!--IMG:Screenshot 2026-10-24 183433.png|Zones: per-zone system assessment, security status, and estimated device count; select one to set its official status.-->


## Screen 4 — Targeted Feedback

Ask associated students a neutral question.

- Pick a **building** and optional **floor**, type a neutral question.
- A **Demo recipients** box lists exactly which seeded students would receive the push (a
  demo aid, security-only, names only, no device IDs) so you can verify targeting.
- **Send** routes the question to associated students and shows the eligible device count.
- **Sent requests & responses** tracks each request with live Yes/No/Unsure tallies.

Feedback is evidence for human assessment, never automatic confirmation; identities and
locations are never shown.

<!--IMG:Screenshot 2026-10-24 183636.png|Targeted Feedback: pick a building/floor, compose a neutral question, and track responses.-->


## Screen 5 — Alerts

Compose and approve official student-facing alerts.

- **Scope toggle:** Campus-wide / Building / Floor (with building/floor pickers as needed).
- **Message** (short, actionable, up to 500 chars).
- **Intended audience** — a live count of eligible simulated devices.
- **Demo recipients** box — which seeded students would receive it (same demo aid as
  Feedback), so you can sign in as them to confirm delivery.
- **Approve & send alert** — requires the authenticated security identity and writes an
  auditable approval record (who, when, audience, content).
- **Alert history** — all sent alerts with scope, source, and time.

No AI output, student report, or automatic flag can send an alert — only an authenticated
dispatcher approval can. Approved alerts are pushed to targeted students instantly.

<!--IMG:Screenshot 2026-10-24 183555.png|Alerts: scope toggle, message, audience preview, and the audit-backed Approve & send action.-->


---

# Two statuses, kept separate

A recurring concept across Zones and the Dashboard:

- **System assessment** (automated, advisory): *potential impact / conflicting evidence /
  insufficient information.* Computed by the evidence engine from reports and field
  observations. Defaults to "insufficient information" — never "safe".
- **Security status** (official, human-only): *unassessed / under investigation / restricted
  / cleared.* Only a dispatcher changes it, and every change is audited.

The evidence engine groups reports into clusters, counts **distinct sources** (so repeated
reports from one device don't inflate corroboration), separates firsthand from hearsay, and
flags contradictions and duplicates. It assists; it never decides.

---

# How the pieces connect (quick reference)

| Student action | Where security sees it |
|---|---|
| Submit report | Dashboard live feed + incident heatmap; Incidents (unassigned); Zones (related reports) |
| Answer feedback | Targeted Feedback tallies; Zones feedback tallies |
| (receives) Alert | Composed/approved in Alerts; shown in Zones alert history |

| Security action | Where the student sees it |
|---|---|
| Send targeted feedback | Student Feedback tab (if in the targeted zone) |
| Approve alert | Student Alerts tab (if in scope or campus-wide) |

Simulated Wi-Fi associations drive both the location suggestion on the student side and the
aggregate crowd-density and audience counts on the security side — always as counts, never
as identities, on any security-facing screen.
