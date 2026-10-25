export type ObservationType = "saw" | "heard" | "was_told";
export type SystemAssessment =
  | "potential_impact"
  | "conflicting_evidence"
  | "insufficient_information";
export type SecurityStatus =
  | "unassessed"
  | "under_investigation"
  | "restricted"
  | "cleared";
export type Scope = "campus" | "building" | "floor";

export interface Analysis {
  kind: "ai" | "rules";
  summary: string | null;
  distress_indicators: string[];
  hazards: string[];
  contradiction_flag: boolean;
  duplicate_flag: boolean;
  source_refs: string[];
}

export interface ReportOut {
  id: number;
  observation_type: ObservationType;
  building_id: number;
  building_name: string;
  floor: number | null;
  description: string | null;
  has_photo: boolean;
  created_at: string;
  incident_id: number | null;
  analysis: Analysis | null;
}

export interface WifiSuggestion {
  building_id: number | null;
  building_name: string | null;
  floor: number | null;
  confidence: number;
  stale: boolean;
  available: boolean;
}

export interface StudentAlert {
  id: number;
  scope: Scope;
  building_name: string | null;
  floor: number | null;
  message: string;
  source: string;
  issued_at: string;
}

export interface StudentFeedbackItem {
  id: number;
  question: string;
  building_name: string | null;
  floor: number | null;
}

export interface IncidentHeatCell {
  building_id: number;
  floor: number | null;
  report_count: number;
  distinct_sources: number;
  firsthand_sources: number;
  hazards: string[];
  duplicate_count: number;
  contradiction: boolean;
  system_assessment: SystemAssessment;
}

export interface CrowdFloor {
  floor: number;
  count: number;
  fresh: boolean;
}
export interface CrowdBuilding {
  building_id: number;
  building_name: string;
  total: number;
  floors: CrowdFloor[];
  stale_or_unknown: number;
}

export interface MapBuilding {
  id: number;
  x: number;
  y: number;
  w: number;
  h: number;
  label: string;
}

export interface ZoneListItem {
  zone_id: number;
  building_id: number;
  building_name: string;
  floor: number | null;
  system_assessment: SystemAssessment;
  security_status: SecurityStatus;
  estimated_device_count: number;
  device_count_fresh: boolean;
}

export interface FieldObservation {
  id: number;
  officer_id: string;
  building_id: number;
  floor: number | null;
  findings: string;
  observed_at: string;
}

export interface ZoneDetail extends ZoneListItem {
  reports: ReportOut[];
  field_observations: FieldObservation[];
  feedback_tallies: Record<string, number>;
  alert_history: StudentAlert[];
  status_history: Array<{
    old_status: string | null;
    new_status: string;
    changed_at: string;
    note: string | null;
  }>;
}

export interface Incident {
  id: number;
  title: string;
  status: string;
  created_at: string;
}
