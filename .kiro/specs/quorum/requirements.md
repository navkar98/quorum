# Quorum — Requirements

## Introduction

Quorum is an AI-assisted campus emergency coordination system for UMass Boston. Students
submit observations; AI and deterministic rules organize incoming information, surface
potential incident clusters, and highlight conflicting evidence. Campus security retains
full authority over official incident statuses, affected zones, feedback requests, and
student alerts. Quorum supplements — never replaces — existing emergency communication.

This document captures requirements as user stories with EARS-style acceptance criteria.
All Wi-Fi data and notifications are simulated for the hackathon.

## Glossary

- **Zone** — a building or a specific floor within a building.
- **Observation type** — Saw (firsthand), Heard, or Was Told (hearsay).
- **System assessment** — automated: potential impact / conflicting evidence /
  insufficient information.
- **Security status** — human-set: unassessed / under investigation / restricted /
  cleared.
- **Distinct source** — a unique reporting device/identity; used so repeated reports do
  not inflate corroboration.

## Requirements

### 1. Student incident reporting

**User story:** As a student, I want to quickly report what I observed, so security gets
timely ground-truth.

#### Acceptance criteria
1. WHEN a student opens the Report tab THEN the system SHALL present observation types
   Saw, Heard, and Was Told as large, accessible touch targets.
2. WHEN a student submits a report THEN the system SHALL require an observation type and a
   location (building, optional floor) and SHALL accept an optional description and one
   optional photo.
3. WHEN a student's device has Wi-Fi association data THEN the system SHALL pre-fill a
   suggested building and floor AND SHALL allow the student to manually override them.
4. WHEN a report is submitted THEN the system SHALL store it and acknowledge immediately,
   WITHOUT waiting for AI analysis.
5. The system SHALL make student reports visible only to security roles; a student SHALL
   NOT be able to retrieve any other student's report or identity.
6. The student interface SHALL avoid unnecessary sound or vibration.

### 2. Student feedback responses

**User story:** As a student, I want to answer security's targeted questions, so they get
corroborating evidence.

#### Acceptance criteria
1. WHEN security has sent a feedback request targeting a student's zone THEN the system
   SHALL display the neutral question with Yes / No / Unsure options.
2. WHEN a student answers THEN the system SHALL record the response and route it only to
   security.
3. A feedback response SHALL NOT automatically verify or dismiss any incident.

### 3. Student response/alerts

**User story:** As a student, I want clear official guidance, so I know what to do.

#### Acceptance criteria
1. WHEN security has issued an alert targeting a student's zone or the campus THEN the
   system SHALL display the short approved instruction with its official source and
   issuance time.
2. The response view SHALL NOT include unverified incident details, distress scores,
   rumor counts, or other students' locations.
3. The system SHALL support building-specific, floor-specific, and campus-wide alerts.

### 4. Wi-Fi-based zone identification (simulated)

**User story:** As the system, I want to estimate device zones from simulated Wi-Fi, so
reporting and targeting are easier.

#### Acceptance criteria
1. The system SHALL estimate building and floor for a device from simulated access-point
   association data.
2. WHEN association data is unavailable, outdated, or low-confidence THEN the system SHALL
   indicate that and SHALL allow manual location entry.
3. The system SHALL maintain estimated connected-device counts per zone with a freshness
   timestamp.
4. Security-facing APIs SHALL expose only aggregate counts — never device identities or
   movement histories.
5. Wi-Fi location SHALL NOT, by itself, establish whether a zone is safe or impacted.

### 5. Security dashboard with two heatmaps

**User story:** As security, I want a live dashboard, so I can assess the campus at a
glance.

#### Acceptance criteria
1. The dashboard SHALL show a simplified campus map, active incidents, recent reports,
   zone assessments, and notifications requiring review.
2. The system SHALL provide an Incident Activity heatmap that groups recent reports by
   location and time and flags unusual clusters, conflicting observations, and possible
   duplicates.
3. The system SHALL provide a Crowd Density heatmap of estimated Wi-Fi device counts by
   building and floor, with freshness and unknown/unassociated indicators.
4. The dashboard SHALL let security switch between the two heatmaps AND SHALL keep them
   conceptually separate (report density ≠ danger; crowd density ≠ safety).
5. The dashboard SHALL clearly distinguish reported observations from confirmed
   incidents.
6. WHEN new reports, feedback, field observations, or alerts occur THEN the dashboard
   SHALL update in near-real-time.

### 6. Incident management

**User story:** As a dispatcher, I want to manage incidents and field observations
quickly.

#### Acceptance criteria
1. Security SHALL be able to create and review incidents and associate reports with an
   incident.
2. Security SHALL be able to view related student reports and AI/rules analysis for an
   incident.
3. Security SHALL be able to record a field observation with reporting officer id,
   observation time, building, floor, and findings.
4. Security SHALL be able to update official incident and zone statuses and view zone
   status change history.

### 7. Incident logs and AI analysis display

**User story:** As security, I want report details and AI analysis clearly separated from
raw observations.

#### Acceptance criteria
1. For each report the system SHALL display original text, attached photo, reported
   building/floor, timestamp, and observation type.
2. The system SHALL display AI/rules outputs: summary, potential distress indicators,
   contradiction and duplicate flags, and source references.
3. AI-generated content SHALL be visibly labeled and distinguishable from original
   observations and dispatcher-entered field reports.
4. WHEN a generated summary cites evidence THEN the system SHALL show the source
   references it is based on.

### 8. Zone management

**User story:** As security, I want a full per-zone picture and official status control.

#### Acceptance criteria
1. WHEN security selects a building/floor THEN the system SHALL display system impact
   assessment, security status, related reports, field observations, estimated device
   count, feedback results, and alert history.
2. System assessment SHALL use: potential impact / conflicting evidence / insufficient
   information. Security status SHALL use: unassessed / under investigation / restricted /
   cleared.
3. Only authorized security SHALL change security status; the system SHALL reject such
   changes from non-security roles AND SHALL write an audit record.
4. An unassessed zone SHALL NOT be automatically labeled safe/cleared.
5. A single negative field observation SHALL NOT automatically clear an entire building.

### 9. Targeted feedback

**User story:** As security, I want to ask associated students a neutral question.

#### Acceptance criteria
1. WHEN security selects a building/floor and composes a neutral question THEN the system
   SHALL show the count of eligible simulated devices before sending.
2. WHEN sent THEN the system SHALL route the question only to associated students and
   SHALL tally Yes/No/Unsure responses.
3. The system SHALL NOT expose respondent identities or individual device locations.
4. Feedback results SHALL be presented as evidence for human assessment, not automatic
   confirmation.

### 10. Alert management

**User story:** As security, I want to compose and approve official alerts with an audit
trail.

#### Acceptance criteria
1. Security SHALL be able to target buildings, floors, or the whole campus; preview the
   intended audience (eligible device count); and approve+send a simulated alert.
2. WHEN an alert is approved THEN the system SHALL require an authenticated security
   identity AND SHALL write an auditable approval record (who, when, audience, content).
3. No AI output, student report, or automatic flag SHALL independently publish an alert.
4. Security SHALL be able to view alert history.

### 11. Evidence correlation engine

**User story:** As security, I want observations grouped and conflicts surfaced, so I can
focus.

#### Acceptance criteria
1. The engine SHALL process student reports, dispatcher field observations, simulated
   Wi-Fi zone context, and report timestamps/locations.
2. The engine SHALL group related observations, identify potential incident clusters, and
   suggest zones requiring review.
3. The engine SHALL highlight contradictions and possible duplicates and SHALL
   distinguish firsthand from hearsay.
4. The engine SHALL count distinct sources for corroboration; repeated reports from one
   device SHALL NOT increase the distinct-source count.
5. The engine SHALL update assessments when new information arrives.
6. The engine SHALL NOT declare an incident real, fake, or resolved.

### 12. AI integration (modular, fallback-safe)

**User story:** As a developer, I want AI behind a swappable interface with a safe
fallback.

#### Acceptance criteria
1. The system SHALL expose a single AIProvider interface used for summarization, image
   description (without identifying people), observation extraction, distress/hazard
   detection, and uncertainty/contradiction highlighting.
2. AI analysis SHALL run asynchronously so report submission is never blocked.
3. WHEN AI is unavailable or times out THEN the system SHALL run deterministic fallback
   rules AND label the result accordingly (rules vs ai).
4. AI SHALL NOT approve alerts or change official zone statuses.
5. The system SHALL treat all uploaded content as untrusted input.

### 13. Backend, database, roles

**User story:** As a developer, I want a role-aware API over the provided schema.

#### Acceptance criteria
1. The backend SHALL use the schema in `db/schema.sql` as provided and SHALL NOT modify
   it without approval.
2. The backend SHALL implement role-based access control for student vs security
   operations, enforced server-side.
3. The backend SHALL provide a seed loader for the synthetic data files.
4. The backend SHALL provide near-real-time dashboard updates.
5. The backend SHALL NOT log report contents or device identifiers unnecessarily.

### 14. Scenario simulator (demo)

**User story:** As a presenter, I want to replay a synthetic scenario chronologically.

#### Acceptance criteria
1. The system SHALL replay synthetic reports in chronological order, producing reports,
   feedback, and field observations that appear live on the dashboard.
2. The system SHALL allow a real phone to submit a report while the scenario runs.
3. The demo SHALL exercise the full flow: reports → dashboard → incident heatmap update →
   crowd-density heatmap → AI/rules cluster + contradiction → dispatcher field
   observation → updated assessment → manual zone status change → targeted feedback →
   approved zone alert → student receives alert.
4. The system SHALL use only simulated notifications and Wi-Fi data.
