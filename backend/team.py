"""Ticket runs for the Campus Customs agent team.

A ticket run starts the boss on one ticket. The boss routes it to the one
specialist its ticket type calls for (agents.ROUTING); that specialist brings
in others only as needed. Every agent run is appended to
output/audit_trail.json. Tickets run one at a time because they share cash.

    python backend/team.py --ticket 101         # one ticket
    python backend/team.py --all                # every open ticket, in id order
    python backend/team.py --reset --all        # restore the working DB first

--reset copies data/campus_customs.db over data/campus_customs_new.db. The
original is never written. The audit trail is never wiped.
"""

import argparse
import asyncio
import shutil
import stat
import uuid
from pathlib import Path

from fastmcp import Client

import audit
import events
from pydantic_ai import RunUsage

from agents import MAX_SPECIALISTS_PER_TICKET, MODEL_NAME, ROUTING, TICKET_USAGE_LIMITS, mcp_transport, run_agent, shop_mcp
from models import AuditRecord, BossDecision, TeamDeps, TicketRouting

ROOT = Path(__file__).resolve().parent.parent
ORIGINAL_DB = ROOT / "data" / "campus_customs.db"
WORKING_DB = ROOT / "data" / "campus_customs_new.db"


def reset_working_db() -> None:
    """Restore the working copy from the untouched original."""
    shutil.copyfile(ORIGINAL_DB, WORKING_DB)
    WORKING_DB.chmod(WORKING_DB.stat().st_mode | stat.S_IWUSR)


async def open_ticket_ids() -> list[int]:
    async with Client(mcp_transport()) as client:
        board = (await client.call_tool("desk_board_overview", {"status": "open"})).data
    return [t["id"] for t in board["tickets"]]


async def ticket_type(ticket_id: int) -> str:
    async with Client(mcp_transport()) as client:
        dossier = (await client.call_tool("ticket_dossier_fetch", {"ticket_id": ticket_id})).data
    return dossier["ticket"]["type"]


async def run_ticket(ticket_id: int, ticket_run_id: str | None = None) -> BossDecision:
    ticket_run_id = ticket_run_id or uuid.uuid4().hex[:12]
    t_type = await ticket_type(ticket_id)
    routing = TicketRouting(ticket_type=t_type, routed_agent=ROUTING.get(t_type))
    deps = TeamDeps(ticket_id=ticket_id, ticket_run_id=ticket_run_id, agent="boss", role="lead",
                    agent_run_id=uuid.uuid4().hex[:12], chain=["boss"], depth=0, routing=routing)
    usage = RunUsage()
    first = routing.routed_agent or "no one (unknown type: set blocked and ask a human to route it)"
    prompt = (f"Work ticket {ticket_id} (type {t_type}). Open it, route it with route_ticket (it goes to {first}), "
              "make the call, and finish with the ticket's status set and your BossDecision.")
    record = AuditRecord(record_type="ticket_run", ticket_run_id=ticket_run_id, ticket_id=ticket_id,
                         agent="team", model=MODEL_NAME, started_at=audit.now(), finished_at="",
                         status="ok", prompt=prompt)
    events.emit("run_started", ticket_id=ticket_id, ticket_run_id=ticket_run_id, prompt=prompt,
                routed_to=routing.routed_agent)
    try:
        async with shop_mcp:  # one MCP server process for the whole ticket run
            result = await run_agent("boss", prompt, deps, BossDecision, usage=usage)
        record.output = result.model_dump(mode="json")
        return result
    except Exception as e:
        record.status, record.error = "error", f"{type(e).__name__}: {e}"
        raise
    finally:
        record.finished_at = audit.now()
        record.routing = {
            "ticket_type": t_type,
            "routed_to": routing.routed_agent,
            "specialists_joined": routing.joined,
            "handoffs": [h.__dict__ for h in routing.handoffs],
            "max_specialists": MAX_SPECIALISTS_PER_TICKET,
        }
        record.usage = {"requests": usage.requests, "tool_calls": usage.tool_calls,
                        "input_tokens": usage.input_tokens, "output_tokens": usage.output_tokens,
                        "limits": {"request_limit": TICKET_USAGE_LIMITS.request_limit,
                                   "tool_calls_limit": TICKET_USAGE_LIMITS.tool_calls_limit,
                                   "total_tokens_limit": TICKET_USAGE_LIMITS.total_tokens_limit}}
        audit.append(record)
        events.emit("run_finished" if record.status == "ok" else "run_failed", ticket_id=ticket_id,
                    ticket_run_id=ticket_run_id, output=record.output, error=record.error, routing=record.routing)


async def run_board() -> dict[int, BossDecision | str]:
    results: dict[int, BossDecision | str] = {}
    for ticket_id in await open_ticket_ids():
        try:
            results[ticket_id] = await run_ticket(ticket_id)
        except Exception as e:  # one failed ticket shouldn't stop the board; it's in the audit trail
            results[ticket_id] = f"{type(e).__name__}: {e}"
    return results


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    target = p.add_mutually_exclusive_group(required=True)
    target.add_argument("--ticket", type=int)
    target.add_argument("--all", action="store_true")
    p.add_argument("--reset", action="store_true", help="restore the working DB from the original first")
    args = p.parse_args()

    if args.reset:
        reset_working_db()
        print(f"Reset {WORKING_DB.name} from {ORIGINAL_DB.name}")
    if args.all:
        for tid, res in asyncio.run(run_board()).items():
            print(f"\n=== ticket {tid}\n{res if isinstance(res, str) else res.model_dump_json(indent=2)}")
    else:
        print(asyncio.run(run_ticket(args.ticket)).model_dump_json(indent=2))


if __name__ == "__main__":
    main()
