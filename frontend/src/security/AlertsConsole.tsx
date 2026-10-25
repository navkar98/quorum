import { useCallback, useEffect, useState } from "react";
import { api, Session } from "../shared/api";
import { Scope, StudentAlert } from "../shared/types";
import { LiveEvent } from "./useLiveEvents";

export default function AlertsConsole({ session, events }: { session: Session; events: LiveEvent[] }) {
  const [buildings, setBuildings] = useState<Array<{ id: number; name: string; floors: number }>>([]);
  const [scope, setScope] = useState<Scope>("building");
  const [buildingId, setBuildingId] = useState<number | "">("");
  const [floor, setFloor] = useState<number | "">("");
  const [message, setMessage] = useState("");
  const [audience, setAudience] = useState<number | null>(null);
  const [recipients, setRecipients] = useState<Array<{ id: number; display_name: string }>>([]);
  const [history, setHistory] = useState<StudentAlert[]>([]);

  useEffect(() => { api.buildings().then(setBuildings); }, []);
  const selected = buildings.find((b) => b.id === buildingId);

  // Demo aid: which seeded students would receive this alert.
  useEffect(() => {
    if (scope !== "campus" && buildingId === "") { setRecipients([]); return; }
    if (scope === "floor" && floor === "") { setRecipients([]); return; }
    api.recipientsPreview(
      session.token, scope,
      scope === "campus" ? null : Number(buildingId),
      scope === "floor" ? Number(floor) : null)
      .then((r) => setRecipients(r.recipients))
      .catch(() => setRecipients([]));
  }, [scope, buildingId, floor, session.token]);

  const loadHistory = useCallback(async () => {
    setHistory(await api.get<StudentAlert[]>("/alerts", session.token));
  }, [session.token]);
  useEffect(() => { loadHistory(); }, [loadHistory, events.length]);

  const preview = useCallback(async () => {
    if (scope !== "campus" && buildingId === "") { setAudience(null); return; }
    if (scope === "floor" && floor === "") { setAudience(null); return; }
    const res = await api.post<{ audience_device_count: number }>("/alerts/preview", session.token, {
      scope, building_id: scope === "campus" ? null : Number(buildingId),
      floor: scope === "floor" ? Number(floor) : null,
    });
    setAudience(res.audience_device_count);
  }, [scope, buildingId, floor, session.token]);
  useEffect(() => { preview(); }, [preview]);

  async function approveAndSend() {
    if (!message.trim()) return;
    if (scope !== "campus" && buildingId === "") return;
    await api.post("/alerts", session.token, {
      scope,
      building_id: scope === "campus" ? null : Number(buildingId),
      floor: scope === "floor" ? Number(floor) : null,
      message: message.trim(),
    });
    setMessage("");
    loadHistory();
  }

  return (
    <div>
      <h2>Alert management</h2>
      <div className="note-banner">
        Every alert requires your authenticated approval and is recorded in an audit log.
        No AI output, student report, or automatic flag can send an alert on its own.
      </div>
      <div className="row">
        <div className="col">
          <div className="card">
            <h3>Compose official alert</h3>
            <div className="toggle-group" style={{ display: "flex" }}>
              {(["campus", "building", "floor"] as Scope[]).map((s) => (
                <button key={s} className={scope === s ? "active" : ""} onClick={() => setScope(s)}>
                  {s === "campus" ? "Campus-wide" : s === "building" ? "Building" : "Floor"}
                </button>
              ))}
            </div>
            {scope !== "campus" && (
              <select className="sec-input" value={buildingId} onChange={(e) => { setBuildingId(Number(e.target.value)); setFloor(""); }}>
                <option value="">Select building…</option>
                {buildings.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}
              </select>
            )}
            {scope === "floor" && (
              <select className="sec-input" value={floor} onChange={(e) => setFloor(e.target.value === "" ? "" : Number(e.target.value))}>
                <option value="">Select floor…</option>
                {selected && Array.from({ length: selected.floors }, (_, i) => i + 1).map((f) => <option key={f} value={f}>Floor {f}</option>)}
              </select>
            )}
            <textarea className="sec-input" placeholder="Short, actionable instruction (max 500 chars)"
              maxLength={500} value={message} onChange={(e) => setMessage(e.target.value)} />
            <div className="feed-item" style={{ borderBottom: "none" }}>
              Intended audience: <strong>{audience == null ? "—" : `${audience} device${audience === 1 ? "" : "s"}`}</strong>
            </div>
            {(scope === "campus" || buildingId !== "") && (
              <div className="recipients-preview">
                <div className="muted" style={{ fontSize: 12, marginBottom: 4 }}>
                  Demo recipients ({recipients.length}) — sign in as these students to verify the alert:
                </div>
                {recipients.length === 0
                  ? <span className="muted" style={{ fontSize: 12 }}>No students currently in this zone.</span>
                  : recipients.map((r) => <span key={r.id} className="chip">{r.display_name}</span>)}
              </div>
            )}
            <button className="sec-btn danger" onClick={approveAndSend}
              disabled={!message.trim() || (scope !== "campus" && buildingId === "") || (scope === "floor" && floor === "")}>
              Approve & send alert
            </button>
          </div>
        </div>
        <div className="col" style={{ flex: 2 }}>
          <div className="card">
            <h3>Alert history</h3>
            {history.length === 0 && <p className="muted">No alerts sent.</p>}
            {history.map((a) => (
              <div key={a.id} className="feed-item">
                <div>{a.message}</div>
                <div className="muted" style={{ fontSize: 12 }}>
                  {a.scope === "campus" ? "Campus-wide" : a.scope === "building" ? a.building_name : `${a.building_name}, floor ${a.floor}`}
                  {" · "}{a.source} · {new Date(a.issued_at).toLocaleString()}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
