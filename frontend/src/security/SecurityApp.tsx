import { useEffect, useState } from "react";
import { NavLink, Navigate, Route, Routes } from "react-router-dom";
import { api, clearSession, loadSession, saveSession, Session } from "../shared/api";
import { useLiveEvents } from "./useLiveEvents";
import Dashboard from "./Dashboard";
import Incidents from "./Incidents";
import Zones from "./Zones";
import FeedbackConsole from "./FeedbackConsole";
import AlertsConsole from "./AlertsConsole";

export default function SecurityApp() {
  const [session, setSession] = useState<Session | null>(() => loadSession("security"));
  if (!session) return <SecurityLogin onLogin={(s) => { saveSession("security", s); setSession(s); }} />;
  return <Console session={session} onLogout={() => { clearSession("security"); setSession(null); }} />;
}

function Console({ session, onLogout }: { session: Session; onLogout: () => void }) {
  const { events, connected } = useLiveEvents(session.token);
  const [scenario, setScenario] = useState<{ running: boolean; sent: number; total: number }>({
    running: false, sent: 0, total: 0,
  });

  async function refreshScenario() {
    try { setScenario(await api.get("/scenario/status", session.token)); } catch { /* ignore */ }
  }
  useEffect(() => { refreshScenario(); }, [events.length]);

  return (
    <div className="security-shell">
      <aside className="sidebar">
        <h1>Quorum</h1>
        <div className="role">
          <span className="live-dot" style={{ background: connected ? "#22c55e" : "#94a3b8" }} />
          {session.display_name}
        </div>
        <nav>
          <NavLink to="dashboard">Dashboard</NavLink>
          <NavLink to="incidents">Incidents</NavLink>
          <NavLink to="zones">Zones</NavLink>
          <NavLink to="feedback">Targeted Feedback</NavLink>
          <NavLink to="alerts">Alerts</NavLink>
        </nav>
        <div className="scenario-ctl">
          <div className="role" style={{ marginBottom: 8 }}>Demo scenario</div>
          {scenario.running ? (
            <>
              <div className="muted" style={{ fontSize: 12, marginBottom: 8 }}>
                Replaying… {scenario.sent}/{scenario.total}
              </div>
              <button className="sec-btn danger" style={{ width: "100%" }}
                onClick={() => api.post("/scenario/stop", session.token).then(refreshScenario)}>
                Stop
              </button>
            </>
          ) : (
            <button className="sec-btn" style={{ width: "100%" }}
              onClick={() => api.post("/scenario/start", session.token).then(refreshScenario)}>
              Start scenario
            </button>
          )}
          <button className="sec-btn ghost" style={{ width: "100%", marginTop: 8 }}
            disabled={scenario.running}
            title={scenario.running ? "Stop the scenario first" : "Clear all demo data and restore default zone statuses"}
            onClick={async () => {
              if (!window.confirm(
                "Reset the demo? This clears all reports, incidents, field observations, " +
                "feedback, and alerts, and returns every zone to 'Unassessed'. " +
                "Structural data (buildings, users, Wi-Fi) is kept."
              )) return;
              await api.post("/scenario/reset", session.token);
              refreshScenario();
            }}>
            Reset demo data
          </button>
          <button className="sec-btn ghost" style={{ width: "100%", marginTop: 8 }} onClick={onLogout}>
            Sign out
          </button>
        </div>
      </aside>
      <div className="content">
        <Routes>
          <Route index element={<Navigate to="dashboard" replace />} />
          <Route path="dashboard" element={<Dashboard session={session} events={events} />} />
          <Route path="incidents" element={<Incidents session={session} events={events} />} />
          <Route path="zones" element={<Zones session={session} events={events} />} />
          <Route path="feedback" element={<FeedbackConsole session={session} />} />
          <Route path="alerts" element={<AlertsConsole session={session} events={events} />} />
          <Route path="*" element={<Navigate to="dashboard" replace />} />
        </Routes>
      </div>
    </div>
  );
}

function SecurityLogin({ onLogin }: { onLogin: (s: Session) => void }) {
  const [users, setUsers] = useState<Array<{ id: number; role: string; display_name: string }>>([]);
  useEffect(() => { api.listUsers().then((u) => setUsers(u.filter((x) => x.role === "security"))); }, []);
  return (
    <div className="login-box">
      <div className="card">
        <h2 style={{ marginTop: 0 }}>Security sign-in</h2>
        <p className="muted">Select a dispatcher account. All privileged actions are enforced server-side.</p>
        {users.map((u) => (
          <div key={u.id} className="choice security" style={{ marginBottom: 10 }}
            onClick={() => api.session(u.id).then(onLogin)}>
            <span className="choice-title">{u.display_name}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
