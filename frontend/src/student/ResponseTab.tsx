import { useEffect, useState } from "react";
import { api, Session } from "../shared/api";
import { StudentAlert } from "../shared/types";

export default function ResponseTab({ session, pushCount = 0 }: { session: Session; pushCount?: number }) {
  const [alerts, setAlerts] = useState<StudentAlert[]>([]);

  async function load() {
    setAlerts(await api.get<StudentAlert[]>("/alerts/mine", session.token));
  }
  // Refresh immediately on a push, and keep a slow poll as a reliability fallback.
  useEffect(() => {
    load();
    const t = setInterval(load, 15000);
    return () => clearInterval(t);
  }, [session.token]);
  useEffect(() => { if (pushCount > 0) load(); }, [pushCount]);

  return (
    <div>
      <h3 style={{ marginTop: 0 }}>Official guidance</h3>
      {alerts.length === 0 && (
        <div className="empty">No active guidance. Follow normal campus safety instructions.</div>
      )}
      {alerts.map((a) => (
        <div className="alert-card" key={a.id}>
          <p style={{ margin: 0, fontSize: 16 }}>{a.message}</p>
          <div className="source">
            {a.source} ·{" "}
            {a.scope === "campus" ? "Campus-wide" :
              a.scope === "building" ? `${a.building_name}` :
                `${a.building_name}, floor ${a.floor}`}{" "}
            · {new Date(a.issued_at).toLocaleString()}
          </div>
        </div>
      ))}
      <p className="disclaimer">
        Guidance here is approved by campus security. In an emergency, follow official
        instructions and call 911.
      </p>
    </div>
  );
}
