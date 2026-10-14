import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api, ApiError } from "./api";
import { ApprovalDesk } from "./components/Approvals";
import { Court, type Bubble, type CourtHandle } from "./components/Court";
import { PlayByPlay } from "./components/PlayByPlay";
import { buildRecap, Recap } from "./components/Recap";
import { Scoreboard } from "./components/Scoreboard";
import { ResolvedTickets, UnresolvedTickets } from "./components/Tickets";
import { BY_AGENT, money, NEED_LABEL } from "./roster";
import type { AgentEvent, AgentName, Approval, Board, BossDecision, Cash, Dossier, Ticket } from "./types";

const FINISHED: Ticket["status"][] = ["resolved", "waiting_on_approval", "blocked"];
const REFRESH_ON = new Set<AgentEvent["kind"]>(["run_started", "run_finished", "run_failed", "approval_decided", "db_reset", "agent_finished"]);
const clip = (s: unknown, n = 150) => {
  const t = typeof s === "string" ? s : JSON.stringify(s ?? "");
  return t.length > n ? t.slice(0, n) + "…" : t;
};

/** Turn an event into the speech bubble its agent shows on court. */
function bubbleFor(e: AgentEvent): Bubble | null {
  switch (e.kind) {
    case "agent_started":
      return { kind: "said", text: e.role === "lead" ? "Let me see this ticket…" : "On it!" };
    case "thinking":
    case "said":
      if (!String(e.text ?? "").trim()) return null;
      return { kind: e.kind, text: clip(e.text) };
    case "tool_call":
      return { kind: "tool", text: `🔧 ${e.tool}(${clip(e.args, 70)})` };
    case "tool_result":
      return { kind: "result", text: `✅ ${e.tool}: ${clip(e.result, 90)}` };
    case "tool_error":
      return { kind: "error", text: `⚠️ ${e.tool}: ${clip(e.result, 90)}` };
    case "handoff":
      return { kind: "handoff", text: `🏀 Passing to ${BY_AGENT[e.to_agent as AgentName]?.role}: ${NEED_LABEL[String(e.need)] ?? e.need}` };
    case "agent_finished": {
      const o = e.output as { summary?: string; headline?: string } | null;
      return { kind: e.status === "ok" ? "done" : "error", text: e.status === "ok" ? `🏁 ${clip(o?.headline ?? o?.summary, 120)}` : `❌ ${clip(e.error, 100)}` };
    }
    default:
      return null;
  }
}

export default function App() {
  const [board, setBoard] = useState<Board | null>(null);
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [cash, setCash] = useState<Cash | null>(null);
  const [pending, setPending] = useState<Approval[]>([]);
  const [approver, setApprover] = useState(() => localStorage.getItem("approver") ?? "");
  // ?ticket=101 opens the board with that ticket's recap selected (used for the resolved-board screenshots)
  const [selected, setSelected] = useState<number | null>(() => Number(new URLSearchParams(location.search).get("ticket")) || null);
  const [decided, setDecided] = useState<Record<number, Approval[]>>({}); // per ticket, from the DB
  const [dossier, setDossier] = useState<Dossier | null>(null);
  const [onCourt, setOnCourt] = useState<number | null>(null); // ticket ball currently animating on court
  const [toast, setToast] = useState<{ text: string; tone: "ok" | "err" } | null>(null);
  const [offline, setOffline] = useState(false);

  const court = useRef<CourtHandle>(null);
  const lastId = useRef(0);
  const liveFrom = useRef<number | null>(null); // events after this id get animated
  const queue = useRef<Promise<void>>(Promise.resolve());
  const ballState = useRef<{ holder: AgentName; parent: Partial<Record<AgentName, AgentName>>; routed: AgentName | null }>({
    holder: "boss",
    parent: {},
    routed: null,
  });
  const serverId = useRef<string | null>(null);
  const [quietRun, setQuietRun] = useState<string | null>(null); // finished run whose bubbles have faded

  const say = (text: string, tone: "ok" | "err" = "ok") => {
    setToast({ text, tone });
    window.setTimeout(() => setToast(null), 5000);
  };

  const refresh = useCallback(async () => {
    try {
      const [b, c, a] = await Promise.all([api.tickets(), api.cash(), api.approvals()]);
      setBoard(b);
      setCash(c);
      setPending(a.pending);
      setOffline(false);
    } catch (e) {
      setOffline(true);
      if (!(e instanceof ApiError) || e.status !== 0) say(String((e as Error).message), "err");
    }
  }, []);

  // ---- animation director: plays live events on the court, one at a time ----
  // One ticket ball per run. It follows the real handoff chain: Boss -> routed specialist
  // -> helpers, comes back up the chain as each one finishes, and at the end the
  // specialist the ticket was routed to takes the only shot (swish), then it drops.
  const direct = useCallback((e: AgentEvent) => {
    const step = async () => {
      const c = court.current;
      if (!c) return;
      const ball = ballState.current;
      const passTo = async (to: AgentName) => {
        if (ball.holder !== to) await c.pass(ball.holder, to);
        ball.holder = to;
      };
      switch (e.kind) {
        case "run_started":
          setOnCourt(e.ticket_id);
          setSelected(e.ticket_id);
          ball.holder = "boss";
          ball.parent = {};
          ball.routed = (e.routed_to as AgentName | null) ?? null;
          await c.enter(e.ticket_id!, "boss");
          break;
        case "handoff": {
          const from = e.from_agent as AgentName;
          const to = e.to_agent as AgentName;
          if (ball.holder !== from) await passTo(from); // make sure the passer has it
          ball.parent[to] = from;
          await passTo(to);
          break;
        }
        case "agent_finished":
          // a finished specialist hands the ball back to whoever brought them in
          if (e.agent && e.agent !== "boss" && ball.holder === e.agent) await passTo(ball.parent[e.agent] ?? "boss");
          break;
        case "run_finished": {
          const shooter = ball.routed ?? "boss";
          await passTo(shooter);
          await c.shoot(shooter);
          await c.dropOut();
          setOnCourt(null);
          setSelected(e.ticket_id);
          break;
        }
        case "run_failed":
          await c.dropOut();
          setOnCourt(null);
          break;
      }
    };
    queue.current = queue.current.then(step, step);
  }, []);

  // ---- polling ----
  useEffect(() => {
    let stop = false;
    const tick = async () => {
      try {
        let res = await api.events(lastId.current);
        if (stop) return;
        setOffline(false);
        if (serverId.current && res.server_id !== serverId.current) {
          // backend restarted: its feed was rebuilt from the audit trail with new ids
          lastId.current = 0;
          res = await api.events(0);
          setEvents([]);
          liveFrom.current = res.last_id;
        }
        serverId.current = res.server_id;
        if (liveFrom.current === null) {
          liveFrom.current = res.last_id;
          if (res.running) {
            // joined mid-run: put the ball in the boss's hands and animate from here on
            setOnCourt(res.running.ticket_id);
            setSelected(res.running.ticket_id);
            const start = res.events.find((e) => e.kind === "run_started" && e.ticket_run_id === res.running!.ticket_run_id);
            ballState.current = { holder: "boss", parent: {}, routed: (start?.routed_to as AgentName | null) ?? null };
            window.setTimeout(() => court.current?.place(res.running!.ticket_id, "boss"), 50);
          }
        }
        if (res.events.length) {
          lastId.current = res.events[res.events.length - 1].id;
          setEvents((prev) => [...prev, ...res.events.filter((e) => !prev.some((p) => p.id === e.id))]);
          for (const e of res.events) if (e.id > liveFrom.current!) direct(e);
          if (res.events.some((e) => REFRESH_ON.has(e.kind))) refresh();
        }
      } catch {
        if (!stop) setOffline(true);
      }
    };
    tick();
    refresh();
    const fast = window.setInterval(tick, 1000);
    const slow = window.setInterval(refresh, 5000);
    return () => {
      stop = true;
      window.clearInterval(fast);
      window.clearInterval(slow);
    };
  }, [direct, refresh]);

  useEffect(() => localStorage.setItem("approver", approver), [approver]);
  useEffect(() => {
    if (import.meta.env.DEV) Object.assign(window, { __court: court, __direct: direct });
  }, [direct]);

  // ---- derived views ----
  const runOf = useCallback(
    (ticketId: number) => [...events].reverse().find((e) => e.kind === "run_started" && e.ticket_id === ticketId)?.ticket_run_id ?? null,
    [events],
  );
  const currentRunId = useMemo(() => [...events].reverse().find((e) => e.kind === "run_started")?.ticket_run_id ?? null, [events]);
  const currentRun = useMemo(() => events.filter((e) => e.ticket_run_id === currentRunId), [events, currentRunId]);

  const currentRunEnd = currentRun.find((e) => e.kind === "run_finished" || e.kind === "run_failed")?.at ?? null;
  useEffect(() => {
    if (!currentRunEnd || !currentRunId) return;
    // bubbles linger 8s after the final shot (none at all if the run ended before the page loaded)
    const wait = Math.max(0, 8000 - (Date.now() - new Date(currentRunEnd).getTime()));
    const t = window.setTimeout(() => setQuietRun(currentRunId), wait);
    return () => window.clearTimeout(t);
  }, [currentRunEnd, currentRunId]);

  // a 1s clock while a run is live, so a slow model call shows a ticking "waiting" bubble
  const [now, setNow] = useState(() => Date.now());
  const live = !!board?.running && !currentRunEnd;
  useEffect(() => {
    if (!live) return;
    const t = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(t);
  }, [live]);

  const { active, done, bubbles } = useMemo(() => {
    const active = new Set<AgentName>();
    const done = new Set<AgentName>();
    const bubbles: Partial<Record<AgentName, Bubble>> = {};
    const started: AgentName[] = [];
    let lastAt = 0;
    for (const e of currentRun) {
      lastAt = Math.max(lastAt, new Date(e.at).getTime());
      if (!e.agent) continue;
      if (e.kind === "agent_started") started.push(e.agent);
      if (e.kind === "agent_started") {
        active.add(e.agent);
        done.delete(e.agent);
      }
      if (e.kind === "agent_finished") {
        active.delete(e.agent);
        done.add(e.agent);
      }
      const b = bubbleFor(e);
      if (b) bubbles[e.agent] = b;
    }
    // the innermost working agent is the one waiting on the model; say so if it's been quiet a while
    const waiting = [...started].reverse().find((a) => active.has(a));
    const quietFor = Math.round((now - lastAt) / 1000);
    if (live && waiting && lastAt && quietFor >= 4)
      bubbles[waiting] = { kind: "thinking", text: `⏳ Waiting on gpt-6-luna… ${quietFor}s` };
    if (quietRun === currentRunId) for (const k of Object.keys(bubbles)) delete bubbles[k as AgentName];
    return { active, done, bubbles };
  }, [currentRun, quietRun, currentRunId, now, live]);

  const headlines = useMemo(() => {
    const h: Record<number, string> = {};
    for (const e of events)
      if (e.kind === "run_finished" && e.ticket_id && e.output) h[e.ticket_id] = (e.output as BossDecision).headline;
    return h;
  }, [events]);

  const selectedRunId = selected !== null ? runOf(selected) : null;
  const recap = useMemo(
    () => (selectedRunId ? buildRecap(events.filter((e) => e.ticket_run_id === selectedRunId)) : []),
    [events, selectedRunId],
  );

  useEffect(() => {
    if (selected === null) return setDossier(null);
    api.ticket(selected).then(setDossier).catch(() => setDossier(null));
  }, [selected, events.length, pending.length]);

  const tickets = board?.tickets ?? [];
  const running = board?.running ?? null;
  const inPlay = onCourt ?? running?.ticket_id ?? null;
  const unresolved = tickets.filter((t) => !FINISHED.includes(t.status) || t.id === inPlay);
  const resolved = tickets.filter((t) => FINISHED.includes(t.status) && t.id !== inPlay);

  // Who approved/rejected what, straight from each resolved ticket's approvals rows (DB truth,
  // so it stays right across resets and restarts).
  const resolvedKey = resolved.map((t) => `${t.id}:${t.status}`).join(",");
  useEffect(() => {
    const ids = resolvedKey ? resolvedKey.split(",").map((k) => Number(k.split(":")[0])) : [];
    Promise.all(ids.map((id) => api.ticket(id).then((d) => [id, d.approvals] as const).catch(() => [id, []] as const))).then(
      (pairs) => setDecided(Object.fromEntries(pairs)),
    );
  }, [resolvedKey, pending.length]);
  const decisions = useMemo(() => {
    const m: Record<number, string[]> = {};
    for (const [id, list] of Object.entries(decided))
      m[Number(id)] = list
        .filter((a) => a.status === "executed" || a.status === "rejected")
        .map((a) => `${a.decided_by} ${a.status === "executed" ? "approved" : "rejected"} #${a.id} (${a.kind.replace("_", " ")} ${money(a.amount)})`);
    return m;
  }, [decided]);

  // ---- actions ----
  const pick = async (t: Ticket) => {
    try {
      await api.run(t.id);
      setSelected(t.id);
      say(`Ticket #${t.id} is in play. Coach Gloria has the ball.`);
      refresh();
    } catch (e) {
      say((e as Error).message, "err");
    }
  };

  const decide = async (a: Approval, d: "approve" | "reject") => {
    try {
      const r = d === "approve" ? await api.approve(a.id, approver.trim()) : await api.reject(a.id, approver.trim());
      say(r.note);
    } catch (e) {
      say((e as Error).message, "err");
    } finally {
      refresh();
    }
  };

  const reset = async () => {
    if (!window.confirm("Reset the working database to the original values? The audit trail is kept.")) return;
    try {
      await api.reset();
      court.current?.clear();
      setOnCourt(null);
      setSelected(null);
      say("Database reset. All three tickets are back on the rack.");
    } catch (e) {
      say((e as Error).message, "err");
    } finally {
      refresh();
    }
  };

  const selTicket = tickets.find((t) => t.id === selected);

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <div className="brand-title">CAMPUS CUSTOMS</div>
          <div className="brand-sub">Agent Court · ops desk</div>
        </div>
        <Scoreboard cash={cash} />
        <div className="topbar-actions">
          <span className={`conn ${offline ? "off" : "on"}`}>{offline ? "Backend offline" : "Live"}</span>
          <button className="btn ghost" onClick={reset} disabled={!!running}>
            ⟲ Reset DB
          </button>
        </div>
      </header>

      {offline && (
        <div className="banner">
          Can't reach the backend at http://localhost:8000. Start it from <code>backend/</code> with{" "}
          <code>uvicorn main:app --reload --port 8000</code>.
        </div>
      )}

      <main className="layout">
        <div className="main-col">
          <UnresolvedTickets loading={!board} tickets={unresolved} inPlay={inPlay} busy={!!running || onCourt !== null} onPick={pick} />
          <Court ref={court} active={active} done={done} bubbles={bubbles} />
          <ResolvedTickets tickets={resolved} headlines={headlines} decisions={decisions} selected={selected} onSelect={setSelected} />
        </div>
        <aside className="side-col">
          <ApprovalDesk pending={pending} approver={approver} onApprover={setApprover} onDecide={decide} />
          <Recap
            ticketId={selected}
            subject={selTicket ? `${selTicket.subject} · ${selTicket.requester}` : undefined}
            recap={recap}
            dossier={dossier}
            running={running?.ticket_id === selected}
          />
          <PlayByPlay events={events.filter((e) => selected === null || e.ticket_id === selected || e.ticket_id === null)} />
        </aside>
      </main>

      {toast && <div className={`toast ${toast.tone}`}>{toast.text}</div>}
    </div>
  );
}
