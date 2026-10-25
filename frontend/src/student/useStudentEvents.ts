import { useEffect, useRef, useState } from "react";

/**
 * Subscribe to the student's zone-targeted push stream. EventSource cannot set headers,
 * so the token is passed as a query param; the backend validates the student role and
 * only forwards events matching the student's current simulated Wi-Fi zone.
 *
 * Returns a monotonically increasing `pushCount` that bumps whenever a matching event
 * (e.g. a new feedback request or alert) arrives, so tabs can refresh immediately.
 */
export function useStudentEvents(token: string) {
  const [pushCount, setPushCount] = useState(0);
  const [lastType, setLastType] = useState<string | null>(null);
  const [connected, setConnected] = useState(false);
  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    const es = new EventSource(`/api/student/events?token=${encodeURIComponent(token)}`);
    esRef.current = es;
    es.onopen = () => setConnected(true);
    es.onerror = () => setConnected(false);
    es.onmessage = (e) => {
      try {
        const parsed = JSON.parse(e.data);
        if (parsed && parsed.type) {
          setLastType(parsed.type);
          setPushCount((n) => n + 1);
        }
      } catch {
        /* hello / keep-alive */
      }
    };
    return () => es.close();
  }, [token]);

  return { pushCount, lastType, connected };
}
