import { useCallback, useEffect, useState } from "react";
import { api, Session } from "../shared/api";
import { FieldObservation, Incident, ReportOut } from "../shared/types";
import { LiveEvent } from "./useLiveEvents";
import ReportCard from "./ReportCard";

export default function Incidents({ session, events }: { session: Session; events: LiveEvent[] }) {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [reports, setReports] = useState<ReportOut[]>([]);
  const [selected, setSelected] = useState<number | null>(null);
  const [incidentReports, setIncidentReports] = useState<ReportOut[]>([]);
  const [newTitle, setNewTitle] = useState("");
  const [checked, setChecked] = useState<Set<number>>(new Set());
  const [fieldObs, setFieldObs] = useState<Omit<FieldObservation, "id">>({
    officer_id: "", building_id: 0, floor: null, findings: "", observed_at: "",
  });

  const load = useCallback(async () => {
    const [inc, reps] = await Promise.all([
      api.get<Incident[]>("/incidents", session.token),
      api.get<ReportOut[]>("/reports", session.token),
    ]);
    setIncidents(inc);
    setReports(reps);
  }, [session.token]);

  useEffect(() => { load(); }, [load]);
  useEffect(() => { load(); }, [events.length, load]);

  const loadIncidentReports = useCallback(async (id: number) => {
    setIncidentReports(await api.get<ReportOut[]>(`/incidents/${id}/reports`, session.token));
  }, [session.token]);

  useEffect(() => { if (selected) loadIncidentReports(selected); }, [selected, events.length, loadIncidentReports]);

  async function createIncident() {
    if (!newTitle.trim()) return;
    const inc = await api.post<Incident>("/incidents", session.token, { title: newTitle.trim() });
    setNewTitle("");
    setSelected(inc.id);
    load();
  }

  async function attach() {
    if (!selected || checked.size === 0) return;
    await api.post(`/incidents/${selected}/attach`, session.token, { report_ids: [...checked] });
    setChecked(new Set());
    loadIncidentReports(selected);
    load();
  }

  async function addFieldObs() {
    if (!selected || !fieldObs.officer_id || !fieldObs.building_id || !fieldObs.findings) return;
    await api.post(`/incidents/${selected}/field-observations`, session.token, {
      officer_id: fieldObs.officer_id,
      building_id: Number(fieldObs.building_id),
      floor: fieldObs.floor ? Number(fieldObs.floor) : null,
      findings: fieldObs.findings,
    });
    setFieldObs({ officer_id: "", building_id: 0, floor: null, findings: "", observed_at: "" });
    loadIncidentReports(selected);
  }

  const unattached = reports.filter((r) => !r.incident_id);

  return (
    <div>
      <h2>Incident management</h2>
      <div className="row">
        <div className="col">
          <div className="card">
            <h3>Create incident</h3>
            <input className="sec-input" placeholder="Incident title" value={newTitle}
              onChange={(e) => setNewTitle(e.target.value)} />
            <button className="sec-btn" onClick={createIncident}>Create</button>
          </div>
          <div className="card">
            <h3>Incidents</h3>
            {incidents.length === 0 && <p className="muted">None yet.</p>}
            {incidents.map((i) => (
              <div key={i.id} className="feed-item" style={{ cursor: "pointer" }}
                onClick={() => setSelected(i.id)}>
                <strong style={{ color: selected === i.id ? "var(--accent)" : undefined }}>{i.title}</strong>
                <span className="muted"> · {i.status}</span>
              </div>
            ))}
          </div>
          <div className="card">
            <h3>Unassigned reports</h3>
            {unattached.length === 0 && <p className="muted">All reports assigned.</p>}
            {unattached.map((r) => (
              <label key={r.id} className="feed-item" style={{ display: "flex", gap: 8, cursor: "pointer" }}>
                <input type="checkbox" checked={checked.has(r.id)}
                  onChange={(e) => {
                    const next = new Set(checked);
                    e.target.checked ? next.add(r.id) : next.delete(r.id);
                    setChecked(next);
                  }} />
                <span><span className={"badge " + r.observation_type}>{r.observation_type}</span>{" "}
                  {r.building_name}{r.floor != null ? `, fl ${r.floor}` : ""}</span>
              </label>
            ))}
            {selected && checked.size > 0 && (
              <button className="sec-btn" style={{ marginTop: 10 }} onClick={attach}>
                Attach {checked.size} to selected incident
              </button>
            )}
          </div>
        </div>

        <div className="col" style={{ flex: 2 }}>
          {!selected && <div className="card"><p className="muted">Select or create an incident to review its reports, add field observations, and see AI analysis.</p></div>}
          {selected && (
            <>
              <div className="card">
                <h3>Enter field observation (radio)</h3>
                <p className="muted" style={{ fontSize: 12, marginTop: -6 }}>
                  Dispatcher-entered. Kept separate from student reports and AI output.
                </p>
                <input className="sec-input" placeholder="Officer ID (e.g. OFC-204)"
                  value={fieldObs.officer_id} onChange={(e) => setFieldObs({ ...fieldObs, officer_id: e.target.value })} />
                <div style={{ display: "flex", gap: 10 }}>
                  <input className="sec-input" placeholder="Building ID" type="number"
                    value={fieldObs.building_id || ""} onChange={(e) => setFieldObs({ ...fieldObs, building_id: Number(e.target.value) })} />
                  <input className="sec-input" placeholder="Floor" type="number"
                    value={fieldObs.floor ?? ""} onChange={(e) => setFieldObs({ ...fieldObs, floor: e.target.value ? Number(e.target.value) : null })} />
                </div>
                <textarea className="sec-input" placeholder="Findings"
                  value={fieldObs.findings} onChange={(e) => setFieldObs({ ...fieldObs, findings: e.target.value })} />
                <button className="sec-btn" onClick={addFieldObs}>Record observation</button>
              </div>

              <h3 style={{ color: "var(--muted)", textTransform: "uppercase", fontSize: 14 }}>Associated reports</h3>
              {incidentReports.length === 0 && <p className="muted">No reports attached yet.</p>}
              {incidentReports.map((r) => <ReportCard key={r.id} report={r} />)}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
