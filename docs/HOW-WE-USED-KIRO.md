# How We Used Kiro to Build Quorum

Quorum — an AI-assisted campus emergency coordination system for UMass Boston — was built
with Kiro's spec-driven workflow at the center. This document explains, concretely, how
each Kiro capability shaped the project, with pointers to the actual files in the repo.

## Why spec-driven mattered for this project

Quorum isn't a typical CRUD app. Its value depends on a set of **non-negotiable safety
rules** (students can't see each other's reports, AI can't approve alerts, one person
can't fake corroboration, unassessed zones are never auto-marked safe, etc.). Getting
those wrong isn't a bug — it's a trust failure. So instead of jumping to code, we used
Kiro to pin down *what* the system must guarantee before writing *how*. That up-front
rigor is what let two people build a safe, coherent full-stack app in a hackathon window.

The work flowed in the order Kiro encourages: **steering → requirements → design → tasks →
implementation → verification**, iterating as we learned.

---

## 1. Steering files — the project's constitution

Location: `.kiro/steering/`

Steering files are always-on context that every interaction respects. We wrote three so
the assistant never drifted from the project's intent:

- **`product.md`** — who the users are (students vs. security), the core promise
  ("reduce misinformation without surrendering critical decisions to AI"), the authority
  model, and the demo-first scope.
- **`tech.md`** — the architecture decisions (FastAPI + SQLite + React/Vite, SSE for live
  updates, a modular AI provider with a deterministic fallback), the project layout, and
  the commands to run/test everything.
- **`safety.md`** — the 19 non-negotiable safety invariants, each numbered, plus an
  explicit list of which ones must be covered by tests.

Why this helped: every later decision — an API shape, a serializer, a test — could be
checked against these files. When a feature risked exposing device identities or letting
AI act on its own, the steering made the correct call obvious instead of a judgment call.

---

## 2. The spec — requirements, design, tasks

Location: `.kiro/specs/quorum/`

### requirements.md
We captured 14 user stories with **EARS-style acceptance criteria** ("WHEN … THE SYSTEM
SHALL …"). This turned fuzzy goals ("help security assess emergencies") into testable
statements ("the engine SHALL count distinct sources; repeated reports from one device
SHALL NOT increase the distinct-source count"). Each criterion later became something we
could actually verify.

### design.md
Before coding, we settled the architecture: the data model, the API surface, the SSE event
model, the modular AI layer, and — critically — the **evidence correlation engine** design
(how reports are grouped, how distinct sources are counted, how contradictions flip a zone
to "conflicting evidence"). A notable moment: the brief referenced a `db/schema.sql` "as
provided," but none existed in the workspace. Rather than silently invent one, we recorded
that gap in the design, defined the schema explicitly, and treated it as authoritative
going forward — exactly the kind of assumption spec-driven work surfaces early.

### tasks.md
The design was decomposed into a checklist of implementation tasks, each tagged with the
requirements and safety rules it satisfies (e.g. "5.2 Distinct-source corroboration …
(Req 11.3, safety 9-11)"). We worked through them top to bottom — database and backend
foundation first, then the engine and APIs, then the two front-ends, then tests — and
checked tasks off as they landed. This kept a large scope from sprawling and made progress
legible.

---

## 3. Build order driven by priorities

The spec's priority list told us to build the end-to-end core first, then add polish. In
practice that meant:

1. Authoritative schema + synthetic seed data.
2. Backend foundation (FastAPI app, role-based auth, DB layer, SSE event bus).
3. The deterministic evidence engine (the analytical heart).
4. Student and security APIs, serialized so identities never leak.
5. The scenario simulator for the demo.
6. Both React front-ends.
7. Safety and property-based tests.

Because the steering and design were already firm, each layer slotted into a known shape
instead of being reinvented.

---

## 4. Safety-focused testing, including property-based tests

Location: `backend/tests/`

The spec called out property-based testing of critical invariants, so we used `pytest`
plus `hypothesis`:

- **Property test** for the anti-inflation rule: no matter how many times one device
  reports, the distinct-source count equals the number of unique devices, and a single
  repeating device can never reach "potential impact" on its own.
- **Example-based safety tests** for report isolation, aggregate-only Wi-Fi exposure,
  security-only status changes, alert authorization + audit, AI having no authority, and
  default-not-safe statuses.
- A **full end-to-end flow test** mirroring the demo script.

These tests map directly back to the numbered rules in `safety.md`, closing the loop from
requirement to guarantee. They also caught real bugs — e.g. the end-to-end test exposed a
SQL error in the Wi-Fi suggestion query that the unit tests had missed.

---

## 5. Agent hook — automation that enforces the rules

Location: `.kiro/hooks/safety-tests-on-save.json`

We created a Kiro **agent hook** that runs the safety test suite automatically whenever a
backend Python file is saved (`PostFileSave`, matched to `backend/**/*.py`). The intent:
if an edit ever breaks a safety invariant, it's caught immediately rather than at demo
time. It encodes the project's most important rule — *the guardrails are not optional* —
as live automation, not just documentation.

---

## 6. Modular AI with a safe default — and honesty about it

The design kept AI behind a single `AIProvider` interface with a deterministic
`RulesProvider` as the default and an optional LLM provider behind an environment variable.
This was a deliberate, spec-guided choice: the demo must work offline, AI must never block
report submission, and if AI is unavailable the system falls back to rules and labels the
output accordingly. The spec also noted we should verify Kiro CLI support for headless
text/image analysis before depending on it — so the default path depends on nothing
external, and AI is never allowed to approve alerts or change official statuses.

---

## 7. Iterating with Kiro after the core was built

Once the end-to-end demo worked, we used the same assistant-driven loop to refine:

- Added **server-push (SSE) delivery** of feedback/alerts to students, with a zone-matched
  audience predicate — keeping the privacy rule that targeting is by zone, never identity.
- Replaced the placeholder campus map with an **approximate real UMass Boston layout** and
  added a **per-floor hover tooltip** (devices, reports, assessment per floor).
- Spread the seeded students across distinct zones and added a **demo recipients preview**
  so push targeting is easy to verify.
- Added a **"Reset demo data"** control that clears transactional data and restores safe
  default zone statuses — never leaving a zone "cleared".
- Produced documentation (a screen-by-screen guide and this writeup) and a 3-minute demo
  script, generated as both Markdown and Word via a small repo script.

Each change was checked against the steering files, so refinements never quietly violated a
safety rule.

---

## The payoff

Using Kiro this way gave us three things that are hard to get in a 24-hour build:

1. **Correctness by construction** — the safety rules were written down, designed around,
   tested, and enforced by a hook, instead of hoped for.
2. **Coherence at speed** — steering + spec meant two developers could build many moving
   parts (engine, APIs, two apps, simulator) that fit together on the first try.
3. **A clear audit trail** — anyone can read `.kiro/` and see exactly what the system is
   supposed to do and why, which is itself part of Quorum's trust story.

In short: Kiro let us treat *"don't surrender critical decisions to AI"* not as a slogan
but as a specified, tested, enforced property of the software.

---

## Where to look in the repo

| Kiro artifact | Path |
|---|---|
| Product steering | `.kiro/steering/product.md` |
| Tech steering | `.kiro/steering/tech.md` |
| Safety steering | `.kiro/steering/safety.md` |
| Requirements (EARS) | `.kiro/specs/quorum/requirements.md` |
| Design | `.kiro/specs/quorum/design.md` |
| Tasks | `.kiro/specs/quorum/tasks.md` |
| Safety-tests hook | `.kiro/hooks/safety-tests-on-save.json` |
| Safety + property tests | `backend/tests/` |
