import { TICKET_TYPE_LABEL } from "../roster";
import type { Ticket } from "../types";
import { Basketball } from "./Court";

interface UnresolvedProps {
  loading: boolean;
  tickets: Ticket[];
  inPlay: number | null;
  busy: boolean;
  onPick: (t: Ticket) => void;
}

export function UnresolvedTickets({ loading, tickets, inPlay, busy, onPick }: UnresolvedProps) {
  return (
    <section className="rack">
      <h2 className="section-title">Unresolved Tickets</h2>
      {loading && <p className="empty">Loading the board…</p>}
      {!loading && tickets.length === 0 && <p className="empty">No open tickets. Hit Reset to put them back on the rack.</p>}
      <div className="rack-row">
        {tickets.map((t) => {
          const playing = t.id === inPlay;
          const disabled = busy || playing;
          return (
            <button
              key={t.id}
              className={`ticket-ball ${playing ? "in-play" : ""}`}
              disabled={disabled}
              onClick={() => onPick(t)}
              title={busy && !playing ? "One ticket at a time: wait for the current run to finish." : `Send ticket ${t.id} to the team`}
            >
              <Basketball label={t.id} className={`ball-svg ${playing ? "ghost" : "bob"}`} />
              <div className="ticket-card">
                <div className="ticket-id">#{t.id} · {TICKET_TYPE_LABEL[t.type] ?? t.type}</div>
                <div className="ticket-subject">{t.subject}</div>
                <div className="ticket-from">from {t.requester}</div>
                <div className="ticket-cta">
                  {playing ? "In play…" : t.status === "in_progress" ? "Interrupted · tap to rerun" : "Tap to play →"}
                </div>
              </div>
            </button>
          );
        })}
      </div>
    </section>
  );
}

const STATUS_CHIP: Record<string, { label: string; cls: string }> = {
  resolved: { label: "Resolved ✓", cls: "chip-ok" },
  waiting_on_approval: { label: "Needs your approval", cls: "chip-wait" },
  blocked: { label: "Blocked", cls: "chip-block" },
};

interface ResolvedProps {
  tickets: Ticket[];
  headlines: Record<number, string>;
  decisions: Record<number, string[]>;
  selected: number | null;
  onSelect: (id: number) => void;
}

export function ResolvedTickets({ tickets, headlines, decisions, selected, onSelect }: ResolvedProps) {
  return (
    <section className="ground">
      <h2 className="section-title">Resolved Tickets</h2>
      {tickets.length === 0 && <p className="empty">Scored tickets land here.</p>}
      <div className="ground-row">
        {tickets.map((t) => {
          const chip = STATUS_CHIP[t.status] ?? { label: t.status, cls: "" };
          return (
            <button
              key={t.id}
              className={`landed ${selected === t.id ? "selected" : ""}`}
              onClick={() => onSelect(t.id)}
              title="Show the team's recap"
            >
              <Basketball label={t.id} className="ball-svg land" />
              <div className="landed-text">
                <strong>{t.subject}</strong>
                <span>{headlines[t.id] ?? "Worked by the team"}</span>
                {decisions[t.id]?.map((d) => (
                  <span key={d} className="decided">
                    {d}
                  </span>
                ))}
                <span className={`chip ${chip.cls}`}>{chip.label}</span>
              </div>
            </button>
          );
        })}
      </div>
    </section>
  );
}
