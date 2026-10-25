// Thin API client. Token is kept in localStorage per app (student vs security).

export type Role = "student" | "security";

export interface Session {
  token: string;
  role: Role;
  display_name: string;
}

const TOKEN_KEYS: Record<string, string> = {
  student: "quorum_student_session",
  security: "quorum_security_session",
};

export function loadSession(kind: "student" | "security"): Session | null {
  const raw = localStorage.getItem(TOKEN_KEYS[kind]);
  return raw ? (JSON.parse(raw) as Session) : null;
}

export function saveSession(kind: "student" | "security", s: Session) {
  localStorage.setItem(TOKEN_KEYS[kind], JSON.stringify(s));
}

export function clearSession(kind: "student" | "security") {
  localStorage.removeItem(TOKEN_KEYS[kind]);
}

async function request<T>(
  path: string,
  token: string | null,
  init: RequestInit = {}
): Promise<T> {
  const headers: Record<string, string> = {
    ...(init.headers as Record<string, string>),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  if (init.body && !(init.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }
  const res = await fetch(`/api${path}`, { ...init, headers });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${res.status}: ${text}`);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const api = {
  get: <T>(path: string, token: string | null) => request<T>(path, token),
  post: <T>(path: string, token: string | null, body?: unknown) =>
    request<T>(path, token, {
      method: "POST",
      body: body instanceof FormData ? body : body ? JSON.stringify(body) : undefined,
    }),
  // Session helpers (no auth needed).
  listUsers: () =>
    request<Array<{
      id: number;
      role: Role;
      display_name: string;
      location?: {
        building_name: string | null;
        floor: number | null;
        available: boolean;
        stale: boolean;
      };
    }>>("/users", null),
  session: (userId: number) => request<Session>(`/session/${userId}`, null),
  buildings: () =>
    request<Array<{ id: number; name: string; floors: number }>>("/buildings", null),
  // DEMO-ONLY: which seeded students would receive a push for this target.
  recipientsPreview: (
    token: string,
    scope: "campus" | "building" | "floor",
    buildingId?: number | null,
    floor?: number | null
  ) => {
    const params = new URLSearchParams({ scope });
    if (buildingId != null) params.set("building_id", String(buildingId));
    if (floor != null) params.set("floor", String(floor));
    return request<{
      scope: string;
      recipients: Array<{ id: number; display_name: string }>;
      count: number;
    }>(`/demo/recipients?${params.toString()}`, token);
  },
};
