import { useEffect, useRef, useState } from "react";

export interface LiveEvent {
  type: string;
  data: Record<string, unknown>;
  at: number;
}

/**
 * Subscribe to the security SSE stream. EventSource cannot set headers, so the token is
 * passed as a query param; the backend validates the security role before streaming.
 */
export function useLiveEvents(token: string) {
  const [events, setEvents] = useState<LiveEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    const es = new EventSource(`/api/events?token=${encodeURIComponent(token)}`);
    esRef.current = es;
    es.onopen = () => setConnected(true);
    es.onerror = () => {
      // EventSource auto-reconnects. Only show "not connected" if it's actually closed;
      // a transient error while it reconnects should not flip the indicator off.
      setConnected(es.readyState === EventSource.OPEN);
    };
    es.onmessage = (e) => {
      // Any message (including keep-alive) means the stream is alive.
      setConnected(true);
      try {
        const parsed = JSON.parse(e.data);
        if (parsed && parsed.type) {
          setEvents((prev) => [{ ...parsed, at: Date.now() }, ...prev].slice(0, 50));
        }
      } catch {
        /* keep-alive or hello */
      }
    };
    return () => es.close();
  }, [token]);

  return { events, connected };
}
