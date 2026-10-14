import type { AgentEvent, Approval, Board, Cash, Dossier, RunInfo } from "./types";

export const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    });
  } catch {
    throw new ApiError(0, `Can't reach the backend at ${API_URL}. Is uvicorn running?`);
  }
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail ?? body);
    throw new ApiError(res.status, detail);
  }
  return body as T;
}

export const api = {
  tickets: () => call<Board>("/tickets"),
  ticket: (id: number) => call<Dossier>(`/tickets/${id}`),
  run: (id: number) =>
    call<RunInfo & { status: string; events_since: number }>(`/tickets/${id}/run`, { method: "POST" }),
  events: (since: number) =>
    call<{ events: AgentEvent[]; last_id: number; server_id: string; running: RunInfo | null }>(`/events?since=${since}&limit=500`),
  approvals: () => call<{ pending: Approval[] }>("/approvals"),
  approve: (id: number, approver: string) =>
    call<{ note: string; new_balance?: number }>(`/approvals/${id}/approve`, {
      method: "POST",
      body: JSON.stringify({ approver }),
    }),
  reject: (id: number, approver: string, comment?: string) =>
    call<{ note: string }>(`/approvals/${id}/reject`, {
      method: "POST",
      body: JSON.stringify({ approver, comment }),
    }),
  cash: () => call<Cash>("/cash"),
  reset: () => call<{ reset: boolean }>("/reset", { method: "POST" }),
};
