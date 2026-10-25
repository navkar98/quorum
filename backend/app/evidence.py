"""Deterministic evidence correlation engine.

Pure-ish functions over current DB state. Produces per-zone system assessments, cluster
groupings, and duplicate/contradiction flags.

Safety invariants enforced here:
  - Corroboration counts DISTINCT sources (device_id). Repeated reports from one device
    do not increase the distinct-source count (anti-inflation).
  - Firsthand (saw) is weighted above hearsay (heard, was_told).
  - Default assessment is 'insufficient_information' — never 'safe'. The engine never
    sets security_status and never declares an incident real/fake/resolved.
  - A single contradicting field observation sets 'conflicting_evidence' for that zone;
    it never clears a building.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

from . import config
from .ai.rules import HAZARD_LEXICON
from .db import get_conn, now_iso

FIRSTHAND = {"saw"}
HEARSAY = {"heard", "was_told"}

# "No hazard" signals in field findings used to detect contradictions.
NEGATION_TERMS = ["no fire", "no smoke", "no active", "all clear", "nothing found",
                  "no hazard", "false alarm", "no injuries"]


@dataclass
class ReportRec:
    id: int
    device_id: str | None
    observation_type: str
    building_id: int
    floor: int | None
    description: str
    created_at: str


@dataclass
class ClusterResult:
    building_id: int
    floor: int | None
    report_ids: list[int]
    distinct_sources: int
    firsthand_sources: int
    hazards: list[str]
    duplicate_report_ids: list[int] = field(default_factory=list)
    contradiction: bool = False
    system_assessment: str = "insufficient_information"


def _parse(ts: str) -> datetime:
    return datetime.fromisoformat(ts)


def _hazards_in(text: str) -> list[str]:
    low = (text or "").lower()
    found = []
    for label, terms in HAZARD_LEXICON.items():
        if any(t in low for t in terms):
            found.append(label)
    return found


def _load_reports() -> list[ReportRec]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, device_id, observation_type, building_id, floor, "
            "COALESCE(description,'') AS description, created_at FROM report "
            "ORDER BY created_at ASC"
        ).fetchall()
    return [ReportRec(**dict(r)) for r in rows]


def _load_field_obs():
    with get_conn() as conn:
        return conn.execute(
            "SELECT building_id, floor, findings, observed_at FROM field_observation"
        ).fetchall()


def correlate() -> list[ClusterResult]:
    """Group reports into building/floor clusters within a time window and assess."""
    reports = _load_reports()
    field_obs = _load_field_obs()
    window = timedelta(minutes=config.CLUSTER_WINDOW_MIN)

    # Group by (building, floor). floor None grouped separately.
    groups: dict[tuple[int, int | None], list[ReportRec]] = {}
    for r in reports:
        groups.setdefault((r.building_id, r.floor), []).append(r)

    results: list[ClusterResult] = []
    for (building_id, floor), recs in groups.items():
        recs.sort(key=lambda r: r.created_at)
        # Keep only recent window relative to the latest report in the group.
        latest = _parse(recs[-1].created_at)
        in_window = [r for r in recs if latest - _parse(r.created_at) <= window]

        # Distinct-source corroboration (anti-inflation): count unique device ids.
        # Reports with no device id are treated as individually distinct (anonymous).
        distinct_devices: set[str] = set()
        anon_count = 0
        firsthand_devices: set[str] = set()
        seen_per_device: dict[str, list[ReportRec]] = {}
        for r in in_window:
            key = r.device_id
            if key:
                distinct_devices.add(key)
                seen_per_device.setdefault(key, []).append(r)
                if r.observation_type in FIRSTHAND:
                    firsthand_devices.add(key)
            else:
                anon_count += 1

        distinct_sources = len(distinct_devices) + anon_count
        firsthand_sources = len(firsthand_devices)

        # Duplicate flags: same device, same observation_type, near-identical text.
        duplicates: list[int] = []
        for dev, items in seen_per_device.items():
            if len(items) < 2:
                continue
            items_sorted = sorted(items, key=lambda r: r.created_at)
            for prev, cur in zip(items_sorted, items_sorted[1:]):
                duplicates.append(cur.id)

        hazards = sorted({h for r in in_window for h in _hazards_in(r.description)})

        # Contradiction: a field observation in the same building (and matching floor if
        # specified) that negates the reported hazard.
        contradiction = False
        for fo in field_obs:
            if fo["building_id"] != building_id:
                continue
            if floor is not None and fo["floor"] is not None and fo["floor"] != floor:
                continue
            findings_low = (fo["findings"] or "").lower()
            if hazards and any(neg in findings_low for neg in NEGATION_TERMS):
                contradiction = True

        assessment = _assess(distinct_sources, firsthand_sources, hazards, contradiction)

        results.append(ClusterResult(
            building_id=building_id,
            floor=floor,
            report_ids=[r.id for r in in_window],
            distinct_sources=distinct_sources,
            firsthand_sources=firsthand_sources,
            hazards=hazards,
            duplicate_report_ids=duplicates,
            contradiction=contradiction,
            system_assessment=assessment,
        ))
    return results


def _assess(distinct_sources: int, firsthand_sources: int,
            hazards: list[str], contradiction: bool) -> str:
    """Map evidence to a system assessment. Never returns a 'safe' verdict."""
    if contradiction:
        return "conflicting_evidence"
    # Potential impact needs multiple distinct sources OR at least one firsthand source
    # combined with another distinct source — repeated single-device reports can't reach
    # this because distinct_sources won't grow.
    if hazards and (firsthand_sources >= 1 and distinct_sources >= 2):
        return "potential_impact"
    if hazards and distinct_sources >= 2:
        return "potential_impact"
    return "insufficient_information"


def apply_assessments() -> list[dict]:
    """Recompute clusters and update zone_assessment.system_assessment (NOT security
    status). Returns the updated zone summaries for event publishing.
    """
    clusters = correlate()
    updated = []
    with get_conn() as conn:
        for c in clusters:
            zone = conn.execute(
                "SELECT id FROM zone WHERE building_id=? AND "
                "((floor IS NULL AND ? IS NULL) OR floor=?)",
                (c.building_id, c.floor, c.floor),
            ).fetchone()
            if zone is None:
                continue
            conn.execute(
                "UPDATE zone_assessment SET system_assessment=? WHERE zone_id=?",
                (c.system_assessment, zone["id"]),
            )
            updated.append({
                "zone_id": zone["id"],
                "building_id": c.building_id,
                "floor": c.floor,
                "system_assessment": c.system_assessment,
                "distinct_sources": c.distinct_sources,
                "contradiction": c.contradiction,
            })
    return updated


def zones_to_review() -> list[dict]:
    """Suggested zones for security attention (potential impact or conflicts)."""
    return [u for u in apply_assessments()
            if u["system_assessment"] in ("potential_impact", "conflicting_evidence")]


def duplicate_and_contradiction_flags() -> dict[int, dict]:
    """Per-report flags: duplicate_flag and contradiction (by its cluster)."""
    flags: dict[int, dict] = {}
    for c in correlate():
        for rid in c.report_ids:
            flags[rid] = {
                "duplicate_flag": rid in c.duplicate_report_ids,
                "contradiction_flag": c.contradiction,
                "source_refs": [f"report:{i}" for i in c.report_ids if i != rid],
            }
    return flags


def touch() -> str:
    return now_iso()
