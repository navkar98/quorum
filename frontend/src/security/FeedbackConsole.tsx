import { useEffect, useState } from "react";
import { api, Session } from "../shared/api";

interface Results { id: number; question: string; tallies: Record<string, number>; total: number; }

export default function FeedbackConsole({ session }: { session: Session }) {
  const [buildings, setBuildings] = useState<Array<{ id: number; name: string; floors: number }>>([]);
  const [buildingId, setBuildingId] = useState<number | "">("");
  const [floor, setFloor] = useState<number | "">("");
  const [question, setQuestion] = useState("");
  const [sent, setSent] = useState<Array<{ id: number; eligible: number; question: string }>>([]);
  const [results, setResults] = useState<Record<number, Results>>({});
  const [recipients, setRecipients] = useState<Array<{ id: number; display_name: string }>>([]);

  useEffect(() => { api.buildings().then(setBuildings); }, []);

  const selected = buildings.find((b) => b.id === buildingId);

  // Preview which demo students would receive this feedback request (demo aid).
  useEffect(() => {
    if (buildingId === "") { setRecipients([]); return; }
    const scope = floor === "" ? "building" : "floor";
    api.recipientsPreview(session.token, scope, Number(buildingId),
      floor === "" ? null : Number(floor))
      .then((r) => setRecipients(r.recipients))
      .catch(() => setRecipients([]));
  }, [buildingId, floor, session.token]);

  async function send() {
    if (buildingId === "" || !question.trim()) return;
    const res = await api.post<{ id: number; eligible_device_count: number }>("/feedback", session.token, {
      building_id: Number(buildingId),
      floor: floor === "" ? null : Number(floor),
      question: question.trim(),
    });
    setSent((s) => [{ id: res.id, eligible: res.eligible_device_count, question: question.trim() }, ...s]);
    setQuestion("");
  }

  async function refresh(id: number) {
    const res = await api.get<Results>(`/feedback/${id}/results`, session.token);
    setResults((r) => ({ ...r, [id]: res }));
  }
  useEffect(() => {
    const t = setInterval(() => sent.forEach((s) => refresh(s.id)), 4000);
    return () => clearInterval(t);
  }, [sent]);

  return (
    <div>
      <h2>Targeted feedback</h2>
      <div className="row">
        <div className="col">
          <div className="card">
            <h3>Ask associated students a neutral question</h3>
            <select className="sec-input" value={buildingId} onChange={(e) => { setBuildingId(Number(e.target.value)); setFloor(""); }}>
              <option value="">Select building…</option>
              {buildings.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}
            </select>
            <select className="sec-input" value={floor} onChange={(e) => setFloor(e.target.value === "" ? "" : Number(e.target.value))}>
              <option value="">All floors</option>
              {selected && Array.from({ length: selected.floors }, (_, i) => i + 1).map((f) => <option key={f} value={f}>Floor {f}</option>)}
            </select>
            <textarea className="sec-input" placeholder='e.g. "Did you personally observe smoke in your building?"'
              value={question} onChange={(e) => setQuestion(e.target.value)} />
            <button className="sec-btn" onClick={send} disabled={buildingId === "" || !question.trim()}>Send to associated students</button>
            {buildingId !== "" && (
              <div className="recipients-preview">
                <div className="muted" style={{ fontSize: 12, marginBottom: 4 }}>
                  Demo recipients ({recipients.length}) — sign in as these students to verify the push:
                </div>
                {recipients.length === 0
                  ? <span className="muted" style={{ fontSize: 12 }}>No students currently in this zone.</span>
                  : recipients.map((r) => <span key={r.id} className="chip">{r.display_name}</span>)}
              </div>
            )}
            <p className="muted" style={{ fontSize: 12 }}>
              Eligible audience is a count of simulated devices. Responses are tallied only — identities and locations are never shown.
              Feedback is evidence for your assessment, not automatic confirmation.
              <br /><em>The recipients list above is a demo aid and is not part of the operational dashboard.</em>
            </p>
          </div>
        </div>
        <div className="col" style={{ flex: 2 }}>
          <div className="card">
            <h3>Sent requests & responses</h3>
            {sent.length === 0 && <p className="muted">No requests sent.</p>}
            {sent.map((s) => {
              const r = results[s.id];
              return (
                <div key={s.id} className="feed-item">
                  <div>{s.question}</div>
                  <div className="muted" style={{ fontSize: 13 }}>
                    Eligible devices: {s.eligible} · Responses: {r?.total ?? 0}
                    {r && ` (Yes ${r.tallies.yes} · No ${r.tallies.no} · Unsure ${r.tallies.unsure})`}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
