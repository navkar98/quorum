import { useEffect, useRef, useState } from "react";
import { api, Session } from "../shared/api";
import { ObservationType, WifiSuggestion } from "../shared/types";

const OBS: { key: ObservationType; label: string; hint: string }[] = [
  { key: "saw", label: "I saw it", hint: "Firsthand — you witnessed this yourself" },
  { key: "heard", label: "I heard it", hint: "You heard a sound, alarm, or people" },
  { key: "was_told", label: "I was told", hint: "Someone else told you about it" },
];

export default function ReportTab({ session }: { session: Session }) {
  const [buildings, setBuildings] = useState<Array<{ id: number; name: string; floors: number }>>([]);
  const [suggestion, setSuggestion] = useState<WifiSuggestion | null>(null);
  const [obs, setObs] = useState<ObservationType | null>(null);
  const [buildingId, setBuildingId] = useState<number | "">("");
  const [floor, setFloor] = useState<number | "">("");
  const [desc, setDesc] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    api.buildings().then(setBuildings);
    api.get<WifiSuggestion>("/wifi/suggest", session.token).then((s) => {
      setSuggestion(s);
      if (s.available && s.building_id) {
        setBuildingId(s.building_id);
        if (s.floor != null) setFloor(s.floor);
      }
    });
  }, [session.token]);

  const selectedBuilding = buildings.find((b) => b.id === buildingId);

  async function submit() {
    if (!obs || buildingId === "") return;
    setSubmitting(true);
    try {
      const fd = new FormData();
      fd.append("observation_type", obs);
      fd.append("building_id", String(buildingId));
      if (floor !== "") fd.append("floor", String(floor));
      if (desc.trim()) fd.append("description", desc.trim());
      const file = fileRef.current?.files?.[0];
      if (file) fd.append("photo", file);
      await api.post("/reports", session.token, fd);
      setDone(true);
      setObs(null); setDesc("");
      if (fileRef.current) fileRef.current.value = "";
      setTimeout(() => setDone(false), 4000);
    } catch (e) {
      alert("Could not submit report. " + (e as Error).message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div>
      <h3 style={{ marginTop: 0 }}>Report what you observed</h3>
      {done && <div className="toast" role="status">Report received. Security has been notified.</div>}

      <p className="muted" style={{ fontSize: 14 }}>How did you learn about this?</p>
      {OBS.map((o) => (
        <button
          key={o.key}
          className={"big-choice" + (obs === o.key ? " selected" : "")}
          aria-pressed={obs === o.key}
          onClick={() => setObs(o.key)}
        >
          {o.label}
          <small>{o.hint}</small>
        </button>
      ))}

      {suggestion && (
        <div className="suggestion">
          {suggestion.available ? (
            <>📍 Suggested location: <strong>{suggestion.building_name}</strong>
              {suggestion.floor != null ? `, floor ${suggestion.floor}` : ""}{" "}
              <span className="muted">(Wi-Fi estimate{suggestion.stale ? ", may be outdated" : ""}). You can change it below.</span>
            </>
          ) : (
            <span className="muted">📍 Wi-Fi location unavailable or uncertain — please choose your location.</span>
          )}
        </div>
      )}

      <div className="field">
        <label htmlFor="b">Building</label>
        <select id="b" value={buildingId} onChange={(e) => { setBuildingId(Number(e.target.value)); setFloor(""); }}>
          <option value="">Select building…</option>
          {buildings.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}
        </select>
      </div>

      <div className="field">
        <label htmlFor="f">Floor (optional)</label>
        <select id="f" value={floor} onChange={(e) => setFloor(e.target.value === "" ? "" : Number(e.target.value))}>
          <option value="">Whole building / unknown</option>
          {selectedBuilding && Array.from({ length: selectedBuilding.floors }, (_, i) => i + 1).map((fl) =>
            <option key={fl} value={fl}>Floor {fl}</option>)}
        </select>
      </div>

      <div className="field">
        <label htmlFor="d">Description (optional)</label>
        <textarea id="d" value={desc} maxLength={2000} onChange={(e) => setDesc(e.target.value)}
          placeholder="What did you observe?" />
      </div>

      <div className="field">
        <label htmlFor="p">Photo (optional)</label>
        <input id="p" ref={fileRef} type="file" accept="image/png,image/jpeg,image/webp" />
      </div>

      <button className="btn" disabled={!obs || buildingId === "" || submitting} onClick={submit}>
        {submitting ? "Sending…" : "Submit report"}
      </button>
      <p className="disclaimer" style={{ marginTop: 14 }}>
        Your report goes only to campus security. It is not shared with other students.
      </p>
    </div>
  );
}
