import { useCallback, useEffect, useState } from "react";
import { api, Session } from "../shared/api";
import { CrowdBuilding, IncidentHeatCell, MapBuilding } from "../shared/types";
import { LiveEvent } from "./useLiveEvents";
import CampusMap from "./CampusMap";

type Mode = "incident" | "crowd";

export default function Dashboard({ session, events }: { session: Session; events: LiveEvent[] }) {
  const [mode, setMode] = useState<Mode>("incident");
  const [map, setMap] = useState<MapBuilding[]>([]);
  const [landmarks, setLandmarks] = useState<Array<{ label: string; x: number; y: number }>>([]);
  const [incident, setIncident] = useState<IncidentHeatCell[]>([]);
  const [crowd, setCrowd] = useState<CrowdBuilding[]>([]);
  const [summary, setSummary] = useState<{ active_incidents: number; zones_to_review: number; recent_reports: any[] }>({
    active_incidents: 0, zones_to_review: 0, recent_reports: [],
  });

  const load = useCallback(async () => {
    const [m, inc, cr, sum] = await Promise.all([
      api.get<{ buildings: MapBuilding[]; landmarks?: Array<{ label: string; x: number; y: number }> }>("/map", session.token),
      api.get<{ cells: IncidentHeatCell[] }>("/heatmap/incident", session.token),
      api.get<{ buildings: CrowdBuilding[] }>("/heatmap/crowd", session.token),
      api.get<any>("/dashboard/summary", session.token),
    ]);
    setMap(m.buildings);
    setLandmarks(m.landmarks ?? []);
    setIncident(inc.cells);
    setCrowd(cr.buildings);
    setSummary(sum);
  }, [session.token]);

  useEffect(() => { load(); }, [load]);
  useEffect(() => { load(); }, [events.length, load]); // fast path: refresh on any live event
  // Safety net: poll while the dashboard is open so the map still updates even if the
  // SSE stream is buffered (e.g. by the dev proxy) or briefly disconnected.
  useEffect(() => {
    const t = setInterval(load, 3000);
    return () => clearInterval(t);
  }, [load]);

  return (
    <div>
      <h2>Dashboard</h2>
      <div className="stat-row">
        <div className="stat"><div className="n">{summary.active_incidents}</div><div className="l">Active incidents</div></div>
        <div className="stat"><div className="n">{summary.zones_to_review}</div><div className="l">Zones to review</div></div>
        <div className="stat"><div className="n">{summary.recent_reports.length}</div><div className="l">Recent reports</div></div>
      </div>

      <div className="row">
        <div className="col" style={{ flex: 2 }}>
          <div className="toggle-group" role="tablist" aria-label="Heatmap mode">
            <button className={mode === "incident" ? "active" : ""} onClick={() => setMode("incident")}>
              Incident activity
            </button>
            <button className={mode === "crowd" ? "active" : ""} onClick={() => setMode("crowd")}>
              Crowd density
            </button>
          </div>
          <div className="note-banner">
            {mode === "incident"
              ? "Concentration of recent student reports. Reported observations are not confirmed incidents — density alone never proves danger."
              : "Estimated Wi-Fi-connected devices by building. Aggregate counts only, no identities. Not exact occupancy and does not prove safety."}
          </div>
          <CampusMap mode={mode} buildings={map} incidentCells={incident} crowd={crowd} landmarks={landmarks} />
        </div>

        <div className="col">
          <div className="card">
            <h3><span className="live-dot" />Live feed</h3>
            {events.length === 0 && <p className="muted">Waiting for activity…</p>}
            {events.slice(0, 12).map((e, i) => (
              <div className="feed-item" key={i}>
                <strong>{labelEvent(e.type)}</strong>{" "}
                <span className="muted">{describe(e)}</span>
              </div>
            ))}
          </div>

          <div className="card">
            <h3>Attention: clusters & conflicts</h3>
            {incident.filter((c) => c.system_assessment !== "insufficient_information").length === 0 && (
              <p className="muted">No flagged clusters.</p>
            )}
            {incident
              .filter((c) => c.system_assessment !== "insufficient_information")
              .map((c, i) => (
                <div className="feed-item" key={i}>
                  Building {c.building_id}{c.floor != null ? `, floor ${c.floor}` : ""} ·{" "}
                  <span className={"badge " + c.system_assessment}>{labelAssessment(c.system_assessment)}</span>{" "}
                  <span className="muted">
                    {c.distinct_sources} distinct source{c.distinct_sources === 1 ? "" : "s"}
                    {c.contradiction ? " · contradiction" : ""}
                    {c.duplicate_count > 0 ? ` · ${c.duplicate_count} dup` : ""}
                  </span>
                </div>
              ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function labelEvent(t: string): string {
  const m: Record<string, string> = {
    "report.created": "New report",
    "analysis.updated": "Analysis ready",
    "zone.updated": "Zone updated",
    "field_observation.created": "Field observation",
    "feedback.created": "Feedback requested",
    "feedback.response": "Feedback answered",
    "alert.created": "Alert sent",
    "incident.created": "Incident created",
    "scenario.started": "Scenario started",
    "scenario.finished": "Scenario finished",
    "scenario.progress": "Scenario",
  };
  return m[t] ?? t;
}

function describe(e: LiveEvent): string {
  const d = e.data;
  if (e.type === "report.created") return `${d.observation_type} · building ${d.building_id}${d.floor != null ? `, fl ${d.floor}` : ""}`;
  if (e.type === "zone.updated" && d.system_assessment) return String(d.system_assessment);
  if (e.type === "alert.created") return `scope ${d.scope}`;
  if (e.type === "scenario.progress") return `${d.sent}/${d.total}`;
  return "";
}

function labelAssessment(a: string): string {
  return a === "potential_impact" ? "Potential impact"
    : a === "conflicting_evidence" ? "Conflicting evidence" : "Insufficient info";
}
