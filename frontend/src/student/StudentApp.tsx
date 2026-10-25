import { useEffect, useState } from "react";
import { NavLink, Navigate, Route, Routes, useLocation } from "react-router-dom";
import { api, clearSession, loadSession, saveSession, Session } from "../shared/api";
import { useStudentEvents } from "./useStudentEvents";
import ReportTab from "./ReportTab";
import FeedbackTab from "./FeedbackTab";
import ResponseTab from "./ResponseTab";

export default function StudentApp() {
  const [session, setSession] = useState<Session | null>(() => loadSession("student"));

  if (!session) return <StudentLogin onLogin={(s) => { saveSession("student", s); setSession(s); }} />;

  return <StudentShell session={session} onLogout={() => { clearSession("student"); setSession(null); }} />;
}

function StudentShell({ session, onLogout }: { session: Session; onLogout: () => void }) {
  const { pushCount, lastType, connected } = useStudentEvents(session.token);
  const location = useLocation();

  // Track unseen pushes per tab so the tab bar can show a dot until the student opens it.
  const [unseen, setUnseen] = useState<{ feedback: boolean; response: boolean }>({
    feedback: false, response: false,
  });

  useEffect(() => {
    if (pushCount === 0 || !lastType) return;
    const path = location.pathname;
    if (lastType === "feedback.created" && !path.endsWith("/feedback")) {
      setUnseen((u) => ({ ...u, feedback: true }));
    }
    if (lastType === "alert.created" && !path.endsWith("/response")) {
      setUnseen((u) => ({ ...u, response: true }));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pushCount]);

  useEffect(() => {
    if (location.pathname.endsWith("/feedback")) setUnseen((u) => ({ ...u, feedback: false }));
    if (location.pathname.endsWith("/response")) setUnseen((u) => ({ ...u, response: false }));
  }, [location.pathname]);

  return (
    <div className="student-shell">
      <header className="student-header">
        <h2>
          Quorum{" "}
          <span className="live-dot" aria-hidden
            style={{ background: connected ? "#22c55e" : "#64748b" }}
            title={connected ? "Live updates on" : "Reconnecting"} />
        </h2>
        <button
          className="btn secondary"
          style={{ width: "auto", padding: "8px 12px", minHeight: 0 }}
          onClick={onLogout}
        >
          {session.display_name}
        </button>
      </header>
      <main className="student-main">
        <Routes>
          <Route index element={<Navigate to="report" replace />} />
          <Route path="report" element={<ReportTab session={session} />} />
          <Route path="feedback" element={<FeedbackTab session={session} pushCount={pushCount} />} />
          <Route path="response" element={<ResponseTab session={session} pushCount={pushCount} />} />
          <Route path="*" element={<Navigate to="report" replace />} />
        </Routes>
      </main>
      <nav className="tabbar" aria-label="Main navigation">
        <NavLink to="report"><span className="tab-icon" aria-hidden>📝</span>Report</NavLink>
        <NavLink to="feedback">
          <span className="tab-icon" aria-hidden>💬{unseen.feedback && <i className="tab-badge" />}</span>Feedback
        </NavLink>
        <NavLink to="response">
          <span className="tab-icon" aria-hidden>📣{unseen.response && <i className="tab-badge" />}</span>Alerts
        </NavLink>
      </nav>
    </div>
  );
}

interface DemoUser {
  id: number;
  role: string;
  display_name: string;
  location?: { building_name: string | null; floor: number | null; available: boolean; stale: boolean };
}

function locationLabel(loc?: DemoUser["location"]): string {
  if (!loc || !loc.building_name) return "Location unavailable";
  const floor = loc.floor != null ? `, floor ${loc.floor}` : "";
  const qualifier = !loc.available || loc.stale ? " (uncertain)" : "";
  return `${loc.building_name}${floor}${qualifier}`;
}

function StudentLogin({ onLogin }: { onLogin: (s: Session) => void }) {
  const [users, setUsers] = useState<DemoUser[]>([]);
  useEffect(() => { api.listUsers().then((u) => setUsers(u.filter((x) => x.role === "student"))); }, []);

  async function pick(id: number) {
    onLogin(await api.session(id));
  }

  return (
    <div className="student-shell">
      <div className="login-box" style={{ padding: 24 }}>
        <h2>Student sign-in</h2>
        <p className="muted">Pick a demo student. Your location is estimated from simulated campus Wi-Fi.</p>
        {users.map((u) => (
          <button key={u.id} className="big-choice" onClick={() => pick(u.id)}>
            {u.display_name}
            <small>📍 {locationLabel(u.location)}</small>
          </button>
        ))}
        {users.length === 0 && <p className="muted">Loading…</p>}
      </div>
    </div>
  );
}
