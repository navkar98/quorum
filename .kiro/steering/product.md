# Quorum — Product Steering

Quorum is an AI-assisted campus emergency coordination system for UMass Boston. It
reduces misinformation, prevents unnecessary panic, and helps campus security assess
emergencies efficiently. It **supplements** existing university emergency communication
systems — it never replaces them and must never delay existing response procedures.

## Who uses it

- **Students** submit observations (Saw / Heard / Was Told), answer targeted feedback,
  and receive security-approved guidance. Mobile-first.
- **Security / dispatchers** review reports, manage incidents and zones, enter radio
  field observations, request feedback, and approve alerts. Desktop-first.

## Core promise

Reduce emergency misinformation, help campus security dynamically assess potentially
impacted areas, and deliver targeted official guidance **without surrendering critical
decisions to AI**.

## Authority model (non-negotiable)

- Security retains complete authority over official incident statuses, affected zones,
  feedback requests, and student alerts.
- AI and deterministic rules **assist** — they never confirm, dismiss, or resolve an
  incident, never change official zone status, and never publish an alert.
- Humans make all final decisions. Every official decision is auditable.

## Two conceptually separate signals

1. **Incident-report activity** (what students report) — does NOT prove danger.
2. **Crowd density** (estimated Wi-Fi device counts) — does NOT prove safety.

These must never be conflated in UI or logic.

## Demo-first scope

This is a 24-hour, 2-developer hackathon prototype. Prioritize a polished, functional
end-to-end demo over production integrations. All Wi-Fi data and notifications are
**simulated**. Never connect to real university emergency infrastructure.
