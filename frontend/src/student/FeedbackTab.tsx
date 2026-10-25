import { useEffect, useState } from "react";
import { api, Session } from "../shared/api";
import { StudentFeedbackItem } from "../shared/types";

export default function FeedbackTab({ session, pushCount = 0 }: { session: Session; pushCount?: number }) {
  const [items, setItems] = useState<StudentFeedbackItem[]>([]);
  const [answered, setAnswered] = useState<Record<number, string>>({});

  async function load() {
    setItems(await api.get<StudentFeedbackItem[]>("/feedback/mine", session.token));
  }
  // Refresh immediately on a push, and keep a slow poll as a reliability fallback.
  useEffect(() => {
    load();
    const t = setInterval(load, 15000);
    return () => clearInterval(t);
  }, [session.token]);
  useEffect(() => { if (pushCount > 0) load(); }, [pushCount]);

  async function answer(id: number, value: "yes" | "no" | "unsure") {
    await api.post(`/feedback/${id}/respond`, session.token, { answer: value });
    setAnswered((a) => ({ ...a, [id]: value }));
  }

  return (
    <div>
      <h3 style={{ marginTop: 0 }}>Questions from campus security</h3>
      {items.length === 0 && (
        <div className="empty">No questions right now. If security needs input from your area, it will appear here.</div>
      )}
      {items.map((it) => (
        <div className="feedback-card" key={it.id}>
          <p style={{ margin: "0 0 12px", fontSize: 16 }}>{it.question}</p>
          {answered[it.id] ? (
            <p className="muted" style={{ margin: 0 }}>Thanks — you answered “{answered[it.id]}”.</p>
          ) : (
            <>
              <button className="btn answer" onClick={() => answer(it.id, "yes")}>Yes</button>
              <button className="btn answer secondary" onClick={() => answer(it.id, "no")}>No</button>
              <button className="btn answer secondary" onClick={() => answer(it.id, "unsure")}>Unsure</button>
            </>
          )}
        </div>
      ))}
      <p className="disclaimer">
        Your answer helps security assess the situation. It does not by itself confirm or
        dismiss any incident.
      </p>
    </div>
  );
}
