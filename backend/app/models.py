"""Pydantic request/response models.

Security-facing serializers whitelist fields so reporter/device identities are never
leaked. There is deliberately no field for device_id or reporter identity in any
security-facing response model.
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

ObservationType = Literal["saw", "heard", "was_told"]
Answer = Literal["yes", "no", "unsure"]
Scope = Literal["campus", "building", "floor"]
SecurityStatus = Literal["unassessed", "under_investigation", "restricted", "cleared"]
SystemAssessment = Literal[
    "potential_impact", "conflicting_evidence", "insufficient_information"
]


# ---- Student-facing ----
class ReportCreate(BaseModel):
    observation_type: ObservationType
    building_id: int
    floor: Optional[int] = None
    description: Optional[str] = Field(default=None, max_length=2000)


class ReportAck(BaseModel):
    id: int
    created_at: str
    status: str = "received"


class WifiSuggestion(BaseModel):
    building_id: Optional[int]
    building_name: Optional[str]
    floor: Optional[int]
    confidence: float
    stale: bool
    available: bool


class FeedbackAnswer(BaseModel):
    answer: Answer


class StudentAlert(BaseModel):
    id: int
    scope: Scope
    building_name: Optional[str]
    floor: Optional[int]
    message: str
    source: str
    issued_at: str


class StudentFeedbackItem(BaseModel):
    id: int
    question: str
    building_name: Optional[str]
    floor: Optional[int]


# ---- Security-facing (no identities) ----
class ReportAnalysisOut(BaseModel):
    kind: Literal["ai", "rules"]
    summary: Optional[str]
    distress_indicators: list[str]
    hazards: list[str]
    contradiction_flag: bool
    duplicate_flag: bool
    source_refs: list[str]


class ReportOut(BaseModel):
    id: int
    observation_type: ObservationType
    building_id: int
    building_name: str
    floor: Optional[int]
    description: Optional[str]
    has_photo: bool
    created_at: str
    incident_id: Optional[int]
    analysis: Optional[ReportAnalysisOut] = None
    # NOTE: no reporter_user_id, no device_id — intentionally omitted.


class IncidentCreate(BaseModel):
    title: str


class IncidentOut(BaseModel):
    id: int
    title: str
    status: str
    created_at: str


class AttachReports(BaseModel):
    report_ids: list[int]


class FieldObservationCreate(BaseModel):
    officer_id: str
    building_id: int
    floor: Optional[int] = None
    findings: str
    observed_at: Optional[str] = None


class FieldObservationOut(BaseModel):
    id: int
    officer_id: str
    building_id: int
    floor: Optional[int]
    findings: str
    observed_at: str


class ZoneStatusChange(BaseModel):
    security_status: SecurityStatus
    note: Optional[str] = None


class ZoneStatusHistoryOut(BaseModel):
    old_status: Optional[str]
    new_status: str
    changed_at: str
    note: Optional[str]


class ZoneDetail(BaseModel):
    zone_id: int
    building_id: int
    building_name: str
    floor: Optional[int]
    system_assessment: SystemAssessment
    security_status: SecurityStatus
    estimated_device_count: int
    device_count_fresh: bool
    reports: list[ReportOut]
    field_observations: list[FieldObservationOut]
    feedback_tallies: dict[str, int]
    alert_history: list["StudentAlert"]
    status_history: list[ZoneStatusHistoryOut]


class FeedbackCreate(BaseModel):
    building_id: int
    floor: Optional[int] = None
    question: str


class FeedbackCreated(BaseModel):
    id: int
    eligible_device_count: int


class FeedbackResults(BaseModel):
    id: int
    question: str
    tallies: dict[str, int]
    total: int


class AlertPreview(BaseModel):
    scope: Scope
    building_id: Optional[int] = None
    floor: Optional[int] = None


class AlertPreviewOut(BaseModel):
    audience_device_count: int


class AlertCreate(BaseModel):
    scope: Scope
    building_id: Optional[int] = None
    floor: Optional[int] = None
    message: str = Field(max_length=500)


class AlertOut(BaseModel):
    id: int
    scope: Scope
    building_id: Optional[int]
    building_name: Optional[str]
    floor: Optional[int]
    message: str
    approved_at: str
    source: str
