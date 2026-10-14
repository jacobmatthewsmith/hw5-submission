export type AgentName = "boss" | "inventory" | "accounting" | "facilities" | "customer_service";
export type TicketStatus = "open" | "in_progress" | "waiting_on_approval" | "blocked" | "resolved";

export interface Ticket {
  id: number;
  type: string;
  requester: string;
  subject: string;
  status: TicketStatus;
  created_at: string;
}

export interface RunInfo {
  ticket_id: number;
  ticket_run_id: string;
  started_at: string;
}

export interface Board {
  shop_today: string;
  desk_notes: string | null;
  tickets: Ticket[];
  running: RunInfo | null;
}

export interface Dossier {
  shop_today: string;
  ticket: Ticket & { sku: string | null; size: string | null; qty: number | null; notes: string | null };
  approvals: Approval[];
  drafts: Draft[];
  agent_notes: { id: number; agent: string; status: string; note: string; created_at: string }[];
}

export interface Draft {
  id: number;
  ticket_id: number;
  author: string;
  recipient: string;
  subject: string;
  body: string;
  status: "draft";
  created_at: string;
}

export interface Approval {
  id: number;
  ticket_id: number;
  kind: "invoice_payment" | "rent_payment" | "purchase_order";
  ref_id: number | null;
  vendor_id: number | null;
  sku: string | null;
  size: string | null;
  qty: number | null;
  amount: number;
  account: string;
  reason?: string;
  requested_by: string;
  status?: "pending" | "executed" | "rejected";
  decided_by?: string | null;
  result_note?: string | null;
}

export interface Cash {
  shop_today: string;
  name: string;
  balance: number;
  balance_date: string;
  pending_payment_requests: number;
  available_after_pending: number;
  payments: { id: number; kind: string; ref_id: number; amount: number; paid_at: string; approved_by: string }[];
}

export interface AgentReport {
  agent: AgentName;
  ticket_id: number;
  summary: string;
  technical_summary: string;
  approval_ids: number[];
  draft_ids: number[];
  blockers: string[];
  recommended_next_step: string;
}

export interface BossDecision {
  ticket_id: number;
  final_status: TicketStatus;
  headline: string;
  decision: string;
  technical_summary: string;
  rationale: string;
  agents_consulted: AgentName[];
  waiting_on_human: number[];
  draft_ids: number[];
  next_steps: string[];
}

export interface AgentEvent {
  id: number;
  at: string;
  kind:
    | "server_started" | "run_started" | "run_finished" | "run_failed"
    | "agent_started" | "agent_finished" | "thinking" | "said" | "tool_call" | "tool_result" | "tool_error"
    | "handoff" | "approval_decided" | "db_reset" | "db_replay";
  ticket_id: number | null;
  ticket_run_id: string | null;
  agent: AgentName | null;
  role: "lead" | "routed" | "helper" | null;
  [key: string]: unknown;
}
