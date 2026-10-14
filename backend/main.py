"""FastAPI backend for the Campus Customs ops dashboard.

Start from backend/:  uvicorn main:app --reload --port 8000

Shop data is read through the campus-customs MCP server, the same way the
agents read it. Approve/reject is the only path that moves money: it calls
the human-only MCP tool on a human-mode server, which agents never get.
"""

import asyncio
import uuid
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastmcp import Client
from fastmcp.client.transports import StdioTransport
from fastmcp.exceptions import ToolError
from pydantic import BaseModel, Field

import audit
import events
from agents import MCP_SERVER, ROOT, mcp_transport
from models import AuditRecord
from team import reset_working_db, run_ticket


# ---- one ticket run at a time ---------------------------------------------------
# Tickets share one cash balance, so runs never overlap, and a reset can't happen mid-run.

class RunState:
    current: dict[str, Any] | None = None
    task: asyncio.Task | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    loaded = events.load_from_audit_trail()
    events.emit("server_started", events_from_audit_trail=loaded)
    yield


app = FastAPI(title="Campus Customs Ops", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],  # Vite dev server
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---- MCP helpers ------------------------------------------------------------------

async def call_mcp(tool: str, args: dict[str, Any] | None = None, *, human: bool = False) -> Any:
    transport = (StdioTransport(command=mcp_transport().command, args=[str(MCP_SERVER)],
                                env={"CAMPUS_MCP_ROLE": "human"}, cwd=str(ROOT))
                 if human else mcp_transport())
    try:
        async with Client(transport) as client:
            return (await client.call_tool(tool, args or {})).data
    except ToolError as e:
        msg = str(e)
        raise HTTPException(status_code=404 if msg.startswith("No ") else 400, detail=msg)


# ---- routes ---------------------------------------------------------------------

@app.get("/tickets")
async def list_tickets() -> dict[str, Any]:
    """Every ticket with its status (open, in_progress, waiting_on_approval, blocked, resolved)."""
    board = await call_mcp("desk_board_overview")
    return {**board, "running": RunState.current}


@app.get("/tickets/{ticket_id}")
async def ticket_detail(ticket_id: int) -> dict[str, Any]:
    """One ticket with its linked rows, approval requests, drafts and agent notes."""
    return await call_mcp("ticket_dossier_fetch", {"ticket_id": ticket_id})


@app.post("/tickets/{ticket_id}/run", status_code=202)
async def run_ticket_route(ticket_id: int) -> dict[str, Any]:
    """Start the agent team on one ticket in the background; poll /events to watch it."""
    await call_mcp("ticket_dossier_fetch", {"ticket_id": ticket_id})  # 404 if no such ticket
    if RunState.task and not RunState.task.done():
        raise HTTPException(409, f"Ticket {RunState.current['ticket_id']} is already running; one run at a time.")

    ticket_run_id = uuid.uuid4().hex[:12]
    RunState.current = {"ticket_id": ticket_id, "ticket_run_id": ticket_run_id, "started_at": events.now()}

    async def _run() -> None:
        try:
            await run_ticket(ticket_id, ticket_run_id)
        except Exception:
            pass  # recorded as run_failed in the events feed and the audit trail
        finally:
            RunState.current = None

    RunState.task = asyncio.create_task(_run())
    return {"ticket_id": ticket_id, "ticket_run_id": ticket_run_id, "status": "started",
            "events_since": events.last_id()}


@app.get("/events")
async def list_events(since: int = 0, ticket_id: int | None = None, limit: int = 200) -> dict[str, Any]:
    """Agent events after id `since`: who started, reasoned, said, called which tool, got what back, handed off."""
    batch = events.since(since, ticket_id, min(limit, 500))
    return {"events": batch, "last_id": events.last_id(), "server_id": events.SERVER_ID, "running": RunState.current}


@app.get("/approvals")
async def list_approvals() -> dict[str, Any]:
    """Payment and purchase-order requests waiting for a human."""
    report = await call_mcp("cash_position_report")
    return {"pending": report["pending_approvals"]}


class Decision(BaseModel):
    approver: str = Field(min_length=1, description="Name of the human clicking the button.")
    comment: str | None = None


async def _decide(approval_id: int, decision: str, body: Decision) -> dict[str, Any]:
    started = audit.now()
    result = await call_mcp("human_decision_record", {"approval_id": approval_id, "decision": decision,
                                                      "approver": body.approver, "comment": body.comment}, human=True)
    audit.append(AuditRecord(
        record_type="human_decision", ticket_id=result.get("ticket_id"), agent="human", started_at=started,
        finished_at=audit.now(), status="ok", prompt=f"{body.approver} clicked {decision} on approval {approval_id}",
        output={"approval_id": approval_id, "decision": decision, "approver": body.approver,
                "comment": body.comment, "result": result}))
    events.emit("approval_decided", ticket_id=result.get("ticket_id"), approval_id=approval_id, decision=decision,
                approver=body.approver, result=result)
    if result.get("refused"):
        raise HTTPException(409, result["refused"])
    return result


@app.post("/approvals/{approval_id}/approve")
async def approve(approval_id: int, body: Decision) -> dict[str, Any]:
    """HUMAN ONLY: approve a pending payment (money moves here) or purchase order."""
    return await _decide(approval_id, "approve", body)


@app.post("/approvals/{approval_id}/reject")
async def reject(approval_id: int, body: Decision) -> dict[str, Any]:
    """HUMAN ONLY: reject a pending request. No money moves."""
    return await _decide(approval_id, "reject", body)


@app.get("/cash")
async def cash() -> dict[str, Any]:
    """The checking account's current balance, plus what pending requests would leave."""
    report = await call_mcp("cash_position_report")
    checking = next((a for a in report["cash_accounts"] if a["name"] == "checking"), None)
    if checking is None:
        raise HTTPException(404, "No checking account in cash_accounts")
    return {"shop_today": report["shop_today"], **checking, "payments": report["payments"]}


@app.post("/reset")
async def reset() -> dict[str, Any]:
    """Copy data/campus_customs.db over data/campus_customs_new.db. The audit trail is kept."""
    if RunState.task and not RunState.task.done():
        raise HTTPException(409, "A ticket run is in progress; reset after it finishes.")
    reset_working_db()
    note = "Working DB restored from campus_customs.db; audit trail kept."
    audit.append(AuditRecord(record_type="db_reset", agent="human", started_at=audit.now(), finished_at=audit.now(),
                             status="ok", prompt="Reset button", output={"note": note}))
    events.emit("db_reset", note=note)
    return {"reset": True, "working_db": "data/campus_customs_new.db", "source": "data/campus_customs.db"}
