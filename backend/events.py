"""Live event feed for the dashboard.

Every agent loop step is turned into small, flat events (an agent started,
reasoned, said something, called a tool, got a result, handed off, finished)
the moment it happens, so the board can poll GET /events?since=<id> and
refresh while a run is still going.

The feed lives in memory. On startup it is rebuilt from
output/audit_trail.json, so past runs still show after a server restart. The
audit trail stays the permanent record; this is just a view of it.
"""

import json
import uuid
from typing import Any

from audit import AUDIT_PATH, now
from models import AuditStep

SERVER_ID = uuid.uuid4().hex[:8]  # changes on every backend start; ids restart from 1
_events: list[dict[str, Any]] = []
_next_id = 1
MAX_TEXT = 1_500  # keep events light for polling; the audit trail has everything


def _short(value: Any) -> Any:
    text = value if isinstance(value, str) else json.dumps(value, default=str)
    return text if len(text) <= MAX_TEXT else text[:MAX_TEXT] + " …"


def emit(kind: str, *, ticket_id: int | None = None, ticket_run_id: str | None = None,
         agent: str | None = None, role: str | None = None, at: str | None = None, **data: Any) -> dict[str, Any]:
    global _next_id
    event = {"id": _next_id, "at": at or now(), "kind": kind, "ticket_id": ticket_id,
             "ticket_run_id": ticket_run_id, "agent": agent, "role": role, **data}
    _next_id += 1
    _events.append(event)
    return event


def emit_step(step: AuditStep, **who: Any) -> None:
    """Flatten one agent-loop step into events: what the agent thought, said, and did."""
    for part in step.parts:
        kind = part.get("part_kind")
        if part.get("tool_name") == "final_result":
            continue  # PydanticAI's structured-output call; the report shows up as agent_finished
        if kind == "thinking":
            emit("thinking", at=step.at, step=step.step, text=_short(part.get("content", "")), **who)
        elif kind == "text":
            emit("said", at=step.at, step=step.step, text=_short(part.get("content", "")), **who)
        elif kind == "tool-call":
            emit("tool_call", at=step.at, step=step.step, tool=part.get("tool_name"), args=part.get("args"), **who)
        elif kind == "tool-return":
            emit("tool_result", at=step.at, step=step.step, tool=part.get("tool_name"),
                 result=_short(part.get("content")), **who)
        elif kind == "retry-prompt":
            emit("tool_error", at=step.at, step=step.step, tool=part.get("tool_name"),
                 result=_short(part.get("content")), **who)


def since(after_id: int = 0, ticket_id: int | None = None, limit: int = 200) -> list[dict[str, Any]]:
    out = [e for e in _events if e["id"] > after_id and (ticket_id is None or e["ticket_id"] == ticket_id)]
    return out[-limit:] if after_id == 0 else out[:limit]


def last_id() -> int:
    return _next_id - 1


def load_from_audit_trail() -> int:
    """Rebuild the feed from past runs in the audit trail. Returns events loaded."""
    if not AUDIT_PATH.exists() or not AUDIT_PATH.stat().st_size:
        return 0
    from agents import NEED_OWNER  # local import: agents imports this module

    records = json.loads(AUDIT_PATH.read_text())
    routed_to = {r["ticket_run_id"]: (r.get("routing") or {}).get("routed_to")
                 for r in records if r["record_type"] == "ticket_run"}
    staged: list[tuple[str, int, str, dict[str, Any]]] = []  # (at, order, kind, fields)
    for rec in records:
        who = {"ticket_id": rec["ticket_id"], "ticket_run_id": rec["ticket_run_id"]}
        if rec["record_type"] == "human_decision":
            o = rec["output"]
            staged.append((rec["finished_at"], 0, "approval_decided", {
                **who, "approval_id": o["approval_id"], "decision": o["decision"],
                "approver": o["approver"], "result": o["result"]}))
            continue
        if rec["record_type"] == "db_replay":
            staged.append((rec["finished_at"], 0, "db_replay", {**who, "note": rec["prompt"]}))
            continue
        if rec["record_type"] == "db_reset":
            staged.append((rec["finished_at"], 0, "db_reset", {**who, "note": rec["output"]["note"]}))
            continue
        if rec["record_type"] == "ticket_run":
            routing = rec.get("routing") or {}
            staged.append((rec["started_at"], 0, "run_started",
                           {**who, "prompt": rec.get("prompt"), "routed_to": routing.get("routed_to")}))
            staged.append((rec["finished_at"], 9, "run_finished" if rec["status"] == "ok" else "run_failed",
                           {**who, "output": rec.get("output"), "error": rec.get("error"), "routing": routing}))
            continue
        who |= {"agent": rec["agent"], "role": rec.get("role"), "agent_run_id": rec.get("agent_run_id")}
        staged.append((rec["started_at"], 2, "agent_started", {**who, "parent_run_id": rec.get("parent_run_id")}))
        returns = {p.get("tool_call_id"): p.get("content") for st in rec.get("steps", [])
                   for p in st["parts"] if p.get("part_kind") == "tool-return"}
        for step in rec.get("steps", []):
            staged.append((step["at"], 3, "__step__", {"step": step, "who": who}))
            # rebuild handoffs from the route_ticket / ask_teammate calls that went through
            for p in step["parts"]:
                if p.get("part_kind") != "tool-call" or p.get("tool_name") not in ("route_ticket", "ask_teammate"):
                    continue
                if str(returns.get(p.get("tool_call_id"), "")).startswith(("Refused", "{} stopped")):
                    continue
                args = p["args"] if isinstance(p["args"], dict) else json.loads(p["args"] or "{}")
                need = "route" if p["tool_name"] == "route_ticket" else args.get("need")
                to = routed_to.get(rec["ticket_run_id"]) if need == "route" else NEED_OWNER.get(need)
                if to:
                    staged.append((step["at"], 4, "handoff", {**who, "from_agent": rec["agent"], "to_agent": to,
                                                              "need": need, "request": args.get("request")}))
        staged.append((rec["finished_at"], 8, "agent_finished",
                       {**who, "status": rec["status"], "output": rec.get("output"), "error": rec.get("error")}))
    for at, _, kind, fields in sorted(staged, key=lambda s: (s[0], s[1])):
        if kind == "__step__":
            step = AuditStep.model_validate(fields["step"])
            if step.node != "end":
                emit_step(step, **fields["who"])
        else:
            emit(kind, at=at, **fields)
    return len(_events)
