import { Link } from "react-router-dom";

export default function Landing() {
  return (
    <div className="landing">
      <div className="landing-card">
        <h1>Quorum</h1>
        <p className="muted">
          AI-assisted campus emergency coordination for UMass Boston. A prototype that
          supplements — never replaces — official emergency communication.
        </p>
        <div className="landing-choices">
          <Link className="choice student" to="/student">
            <span className="choice-title">Student app</span>
            <span className="muted">Report · Feedback · Alerts</span>
          </Link>
          <Link className="choice security" to="/security">
            <span className="choice-title">Security console</span>
            <span className="muted">Dashboard · Incidents · Zones · Alerts</span>
          </Link>
        </div>
        <p className="disclaimer">
          All Wi-Fi data and notifications are simulated. In a real emergency, follow
          official campus safety instructions and call 911.
        </p>
      </div>
    </div>
  );
}
