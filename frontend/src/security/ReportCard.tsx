import { ReportOut } from "../shared/types";

const OBS_LABEL: Record<string, string> = { saw: "Saw", heard: "Heard", was_told: "Was told" };

/** Renders a single report with AI/rules analysis clearly separated from the raw
 *  observation. No reporter identity is ever shown (backend never sends it). */
export default function ReportCard({ report }: { report: ReportOut }) {
  const a = report.analysis;
  return (
    <div className="card" style={{ marginBottom: 12 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <span className={"badge " + report.observation_type}>{OBS_LABEL[report.observation_type]}</span>
        <span className="muted" style={{ fontSize: 12 }}>
          {report.building_name}{report.floor != null ? `, fl ${report.floor}` : ""} · {new Date(report.created_at).toLocaleTimeString()}
        </span>
      </div>
      <p style={{ margin: "10px 0 6px" }}>{report.description || <span className="muted">No description.</span>}</p>
      {report.has_photo && <span className="chip">📷 photo attached</span>}

      {a && (
        <div className="ai-panel" style={{ marginTop: 10 }}>
          <span className="ai-tag">{a.kind === "ai" ? "AI analysis" : "Rules analysis"}</span>
          {a.contradiction_flag && <span className="flag contradiction">⚠ contradiction</span>}
          {a.duplicate_flag && <span className="flag duplicate">⊘ possible duplicate</span>}
          <div style={{ fontSize: 14, marginTop: 4 }}>{a.summary}</div>
          {a.hazards.length > 0 && (
            <div style={{ marginTop: 8 }}>
              <span className="muted" style={{ fontSize: 12 }}>Hazards: </span>
              {a.hazards.map((h) => <span key={h} className="chip">{h}</span>)}
            </div>
          )}
          {a.distress_indicators.length > 0 && (
            <div style={{ marginTop: 6 }}>
              <span className="muted" style={{ fontSize: 12 }}>Distress indicators: </span>
              {a.distress_indicators.map((h) => <span key={h} className="chip">{h}</span>)}
            </div>
          )}
          {a.source_refs.length > 0 && (
            <div className="muted" style={{ fontSize: 11, marginTop: 6 }}>
              Sources: {a.source_refs.join(", ")}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
