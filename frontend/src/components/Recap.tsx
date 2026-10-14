import { useState } from "react";
import { BY_AGENT, NEED_LABEL } from "../roster";
import type { AgentEvent, AgentName, AgentReport, BossDecision, Dossier } from "../types";

export interface AgentRecap {
  key: string;
  visit: number;
  agent: AgentName;
  role: string | null;
  status: string;
  output: AgentReport | BossDecision | null;
  tools: Record<string, number>;
  handoffs: { to: string; need: string }[];
  steps: number;
}

/** Group one ticket run's events into a recap per agent visit (an agent brought back for a
 *  second need gets its own entry), in the order they joined. */
export function buildRecap(events: AgentEvent[]): AgentRecap[] {
  const by = new Map<string, AgentRecap>();
  const visits: Partial<Record<AgentName, number>> = {};
  const get = (e: AgentEvent) => {
    const key = String(e.agent_run_id ?? e.agent);
    if (!by.has(key)) {
      const visit = (visits[e.agent!] = (visits[e.agent!] ?? 0) + 1);
      by.set(key, { key, visit, agent: e.agent!, role: e.role, status: "working", output: null, tools: {}, handoffs: [], steps: 0 });
    }
    return by.get(key)!;
  };
  for (const e of events) {
    if (!e.agent) continue;
    if (e.kind === "handoff") {
      // handoff events name the passer, not its visit: credit the passer's latest visit
      const passer = [...by.values()].reverse().find((v) => v.agent === e.from_agent);
      passer?.handoffs.push({ to: String(e.to_agent), need: String(e.need) });
      continue;
    }
    const r = get(e);
    if (e.kind === "tool_call") r.tools[String(e.tool)] = (r.tools[String(e.tool)] ?? 0) + 1;
    if (e.kind === "said" || e.kind === "tool_call" || e.kind === "thinking") r.steps += 1;
    if (e.kind === "agent_finished") {
      r.status = String(e.status);
      r.output = (e.output as AgentReport | BossDecision | null) ?? null;
    }
  }
  return [...by.values()];
}

const isBoss = (o: AgentReport | BossDecision): o is BossDecision => "decision" in o;

interface Props {
  ticketId: number | null;
  subject?: string;
  recap: AgentRecap[];
  dossier: Dossier | null;
  running: boolean;
}

export function Recap({ ticketId, subject, recap, dossier, running }: Props) {
  const [mode, setMode] = useState<"plain" | "technical">("plain");

  return (
    <section className="panel recap">
      <div className="recap-head">
        <h3 className="panel-title">Team recap{ticketId ? ` · #${ticketId}` : ""}</h3>
        <div className="toggle" role="tablist" aria-label="Summary detail">
          <button role="tab" aria-selected={mode === "plain"} onClick={() => setMode("plain")}>
            Short
          </button>
          <button role="tab" aria-selected={mode === "technical"} onClick={() => setMode("technical")}>
            Technical
          </button>
        </div>
      </div>
      {subject && <p className="recap-subject">{subject}</p>}
      {ticketId === null && <p className="empty">Pick a ticket ball to see what each player did.</p>}
      {ticketId !== null && recap.length === 0 && (
        <p className="empty">{running ? "Tip-off… waiting for the first play." : "This ticket hasn't been played yet."}</p>
      )}

      <ol className="recap-list">
        {recap.map((r) => {
          const who = BY_AGENT[r.agent];
          const o = r.output;
          return (
            <li key={r.key} className={`recap-item jersey-${r.agent}`}>
              <div className="recap-who">
                <span className="recap-num" style={{ background: who.look.jersey }}>
                  {who.look.number}
                </span>
                <strong>{who.role}</strong>
                {r.visit > 1 && <span className="recap-role">visit {r.visit}</span>}
                <span className="recap-role">{r.role === "lead" ? "boss" : r.role}</span>
                <span className={`recap-status s-${r.status}`}>{r.status === "ok" ? "done" : r.status}</span>
              </div>
              {!o && <p className="recap-text muted">{r.status === "working" ? "On the court…" : "No report."}</p>}
              {o && mode === "plain" && (
                <p className="recap-text">
                  {isBoss(o) ? (
                    <>
                      <b>{o.headline}.</b> {o.decision}
                    </>
                  ) : (
                    o.summary
                  )}
                </p>
              )}
              {o && mode === "technical" && (
                <div className="recap-tech">
                  <p className="recap-text">{o.technical_summary}</p>
                  <div className="chips">
                    {Object.entries(r.tools).map(([t, n]) => (
                      <code key={t} className="tool-chip">
                        {t}
                        {n > 1 ? ` ×${n}` : ""}
                      </code>
                    ))}
                    {Object.keys(r.tools).length === 0 && <span className="muted">no MCP tools</span>}
                  </div>
                  {r.handoffs.map((h, i) => (
                    <div key={i} className="handoff-line">
                      🏀 → {BY_AGENT[h.to as AgentName]?.role ?? h.to} ({NEED_LABEL[h.need] ?? h.need})
                    </div>
                  ))}
                  <div className="ids">
                    {isBoss(o) ? (
                      <>
                        status set: <b>{o.final_status}</b>
                        {o.waiting_on_human.length > 0 && <> · waiting on approvals {o.waiting_on_human.join(", ")}</>}
                      </>
                    ) : (
                      <>
                        {o.approval_ids.length > 0 && <>approvals filed: {o.approval_ids.join(", ")} · </>}
                        {o.draft_ids.length > 0 && <>drafts: {o.draft_ids.join(", ")} · </>}
                        {r.steps} loop steps
                      </>
                    )}
                  </div>
                </div>
              )}
            </li>
          );
        })}
      </ol>

      {dossier && dossier.drafts.length > 0 && (
        <div className="drafts">
          <h4>Drafts on the board (not sent)</h4>
          {dossier.drafts.map((d) => (
            <details key={d.id} className="draft">
              <summary>
                ✉️ Draft #{d.id} to {d.recipient}: “{d.subject}”
              </summary>
              <pre>{d.body}</pre>
              <small>written by {BY_AGENT[d.author as AgentName]?.role ?? d.author} · status: draft (never sent)</small>
            </details>
          ))}
        </div>
      )}
    </section>
  );
}
