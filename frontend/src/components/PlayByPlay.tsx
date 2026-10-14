import { BY_AGENT, NEED_LABEL } from "../roster";
import type { AgentEvent, AgentName } from "../types";

const role = (a: unknown) => BY_AGENT[a as AgentName]?.role ?? String(a ?? "");

function brief(v: unknown, n = 90): string {
  const s = typeof v === "string" ? v : JSON.stringify(v ?? "");
  return s.length > n ? s.slice(0, n) + "…" : s;
}

/** One line of play-by-play for an event; null hides it. */
export function describe(e: AgentEvent): { icon: string; text: string } | null {
  switch (e.kind) {
    case "run_started":
      return { icon: "🏁", text: `Tip-off: ticket #${e.ticket_id} → Boss, routed to ${role(e.routed_to) || "nobody"}` };
    case "agent_started":
      return { icon: "🙋", text: `${role(e.agent)} checks in (${e.role})` };
    case "thinking":
    case "said":
      if (!String(e.text ?? "").trim()) return null;
      return { icon: e.kind === "thinking" ? "💭" : "💬", text: `${role(e.agent)}: ${brief(e.text)}` };
    case "tool_call":
      return { icon: "🔧", text: `${role(e.agent)} calls ${e.tool}(${brief(e.args, 60)})` };
    case "tool_result":
      return { icon: "✅", text: `${e.tool} → ${brief(e.result, 70)}` };
    case "tool_error":
      return { icon: "⚠️", text: `${e.tool} refused: ${brief(e.result, 80)}` };
    case "handoff":
      return { icon: "🏀", text: `${role(e.from_agent)} passes to ${role(e.to_agent)} (${NEED_LABEL[String(e.need)] ?? e.need})` };
    case "agent_finished":
      return { icon: e.status === "ok" ? "🏁" : "❌", text: `${role(e.agent)} ${e.status === "ok" ? "finished their part" : e.status}` };
    case "run_finished":
      return { icon: "🏆", text: `Ticket #${e.ticket_id}: ${role(e.routing && (e.routing as { routed_to?: string }).routed_to) || "Boss"} swishes it` };
    case "run_failed":
      return { icon: "🚫", text: `Ticket #${e.ticket_id} run failed: ${brief(e.error)}` };
    case "approval_decided": {
      const r = (e.result ?? {}) as { note?: string; refused?: string };
      return { icon: e.decision === "approve" ? "🟢" : "🔴", text: `${e.approver} ${e.decision}d request #${e.approval_id}: ${brief(r.refused ?? r.note, 80)}` };
    }
    case "db_reset":
      return { icon: "🔄", text: "Working database reset to the original" };
    case "db_replay":
      return { icon: "⏪", text: "Working database restored by replaying recorded writes from the audit trail" };
    default:
      return null;
  }
}

export function PlayByPlay({ events }: { events: AgentEvent[] }) {
  const lines = events
    .map((e) => ({ e, d: describe(e) }))
    .filter((x): x is { e: AgentEvent; d: { icon: string; text: string } } => x.d !== null)
    .slice(-60)
    .reverse();
  return (
    <section className="panel pbp">
      <h3 className="panel-title">Play-by-play</h3>
      {lines.length === 0 && <p className="empty">Quiet court. Pick a ticket to start.</p>}
      <ul>
        {lines.map(({ e, d }) => (
          <li key={e.id} className={`pbp-${e.kind}`}>
            <span className="pbp-icon">{d.icon}</span>
            <span className="pbp-text">{d.text}</span>
            <time>{new Date(e.at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })}</time>
          </li>
        ))}
      </ul>
    </section>
  );
}

