import { useCallback, useEffect, useState } from "react";
import { api, Session } from "../shared/api";
import { SecurityStatus, ZoneDetail, ZoneListItem } from "../shared/types";
import { LiveEvent } from "./useLiveEvents";
import ReportCard from "./ReportCard";

const STATUSES: SecurityStatus[] = ["unassessed", "under_investigation", "restricted", "cleared"];
const STATUS_LABEL: Record<string, string> = {
  unassessed: "Unassessed", under_investigation: "Under investigation",
  restricted: "Restricted", cleared: "Cleared",
  potential_impact: "Potential impact", conflicting_evidence: "Conflicting evidence",
  insufficient_information: "Insufficient information",
};

export default function Zones({ session, events }: { session: Session; events: LiveEvent[] }) {
  const [zones, setZones] = useState<ZoneListItem[]>([]);
  const [selected, setSelected] = useState<number | null>(null);
  const [detail, setDetail] = useState<ZoneDetail | null>(null);
  const [note, setNote] = useState("");

  const load = useCallback(async () => {
    setZones(await api.get<ZoneListItem[]>("/zones", session.token));
  }, [session.token]);
  useEffect(() => { load(); }, [load]);
  useEffect(() => { load(); }, [events.length, load]);

  const loadDetail = useCallback(async (id: number) => {
    setDetail(await api.get<ZoneDetail>(`/zones/${id}`, session.token));
  }, [session.token]);
  useEffect(() => { if (selected) loadDetail(selected); }, [selected, events.length, loadDetail]);

  async function changeStatus(status: SecurityStatus) {
    if (!selected) return;
    await api.post(`/zones/${selected}/status`, session.token, {
      security_status: status, note: note.trim() || null,
    });
    setNote("");
    loadDetail(selected);
    load();
  }

  // Show building-level zones + any floor zones with activity.
  const interesting = zones.filter(
    (z) => z.floor === null || z.system_assessment !== "insufficient_information" ||
      z.estimated_device_count > 0
  );

  return (
    <div>
      <h2>Zone management</h2>
      <div className="row">
        <div className="col">
          <div className="card">
            <h3>Zones</h3>
            <table>
              <thead><tr><th>Zone</th><th>System</th><th>Security</th><th>Devices</th></tr></thead>
              <tbody>
                {interesting.map((z) => (
                  <tr key={z.zone_id} style={{ cursor: "pointer", background: selected === z.zone_id ? "var(--panel-2)" : undefined }}
                    onClick={() => setSelected(z.zone_id)}>
                    <td>{z.building_name}{z.floor != null ? ` · F${z.floor}` : " · all"}</td>
                    <td><span className={"badge " + z.system_assessment}>{STATUS_LABEL[z.system_assessment]}</span></td>
                    <td><span className={"badge " + z.security_status}>{STATUS_LABEL[z.security_status]}</span></td>
                    <td>{z.estimated_device_count}{z.device_count_fresh ? "" : " ⚠"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="col" style={{ flex: 2 }}>
          {!detail && <div className="card"><p className="muted">Select a zone to see the full picture and set its official status.</p></div>}
          {detail && (
            <>
              <div className="card">
                <h3>{detail.building_name}{detail.floor != null ? ` · Floor ${detail.floor}` : " · Whole building"}</h3>
                <div style={{ display: "flex", gap: 20, flexWrap: "wrap", marginBottom: 12 }}>
                  <div><div className="muted" style={{ fontSize: 12 }}>System assessment</div>
                    <span className={"badge " + detail.system_assessment}>{STATUS_LABEL[detail.system_assessment]}</span></div>
                  <div><div className="muted" style={{ fontSize: 12 }}>Security status</div>
                    <span className={"badge " + detail.security_status}>{STATUS_LABEL[detail.security_status]}</span></div>
                  <div><div className="muted" style={{ fontSize: 12 }}>Est. devices</div>
                    <strong>{detail.estimated_device_count}</strong> {detail.device_count_fresh ? "" : <span className="muted">(stale)</span>}</div>
                </div>
                <div className="note-banner">
                  System assessment is automated and advisory. Only you set the official security status.
                  Unassessed zones are never auto-cleared.
                </div>
                <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 10 }}>
                  {STATUSES.map((s) => (
                    <button key={s} className={"sec-btn " + (s === "restricted" ? "danger" : s === detail.security_status ? "" : "ghost")}
                      onClick={() => changeStatus(s)} disabled={s === detail.security_status}>
                      Set {STATUS_LABEL[s]}
                    </button>
                  ))}
                </div>
                <input className="sec-input" placeholder="Optional note for the audit log"
                  value={note} onChange={(e) => setNote(e.target.value)} />
              </div>

              <div className="row">
                <div className="col">
                  <div className="card">
                    <h3>Feedback tallies</h3>
                    <p>Yes: {detail.feedback_tallies.yes ?? 0} · No: {detail.feedback_tallies.no ?? 0} · Unsure: {detail.feedback_tallies.unsure ?? 0}</p>
                    <p className="muted" style={{ fontSize: 12 }}>Counts only — respondent identities are never shown.</p>
                  </div>
                  <div className="card">
                    <h3>Field observations</h3>
                    {detail.field_observations.length === 0 && <p className="muted">None.</p>}
                    {detail.field_observations.map((f) => (
                      <div key={f.id} className="feed-item">
                        <strong>{f.officer_id}</strong> <span className="muted">· {new Date(f.observed_at).toLocaleTimeString()}</span>
                        <div style={{ fontSize: 14 }}>{f.findings}</div>
                      </div>
                    ))}
                  </div>
                </div>
                <div className="col">
                  <div className="card">
                    <h3>Status history (audit)</h3>
                    {detail.status_history.length === 0 && <p className="muted">No changes yet.</p>}
                    {detail.status_history.map((h, i) => (
                      <div key={i} className="feed-item">
                        {STATUS_LABEL[h.old_status ?? ""] ?? h.old_status ?? "—"} → <strong>{STATUS_LABEL[h.new_status]}</strong>
                        <span className="muted"> · {new Date(h.changed_at).toLocaleTimeString()}</span>
                        {h.note && <div className="muted" style={{ fontSize: 12 }}>{h.note}</div>}
                      </div>
                    ))}
                  </div>
                  <div className="card">
                    <h3>Alert history</h3>
                    {detail.alert_history.length === 0 && <p className="muted">None.</p>}
                    {detail.alert_history.map((a) => (
                      <div key={a.id} className="feed-item">{a.message}
                        <div className="muted" style={{ fontSize: 12 }}>{a.source} · {new Date(a.issued_at).toLocaleTimeString()}</div></div>
                    ))}
                  </div>
                </div>
              </div>

              <h3 style={{ color: "var(--muted)", textTransform: "uppercase", fontSize: 14 }}>Related reports</h3>
              {detail.reports.length === 0 && <p className="muted">No reports in this zone.</p>}
              {detail.reports.map((r) => <ReportCard key={r.id} report={r} />)}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
