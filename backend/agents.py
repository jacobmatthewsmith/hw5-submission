"""The five Campus Customs agents and the loop that runs them.

- One model for every agent: gpt-6-luna through Portkey's OpenAI-compatible gateway.
- One prompt file per agent in backend/prompts/.
- Shop facts come only from the campus-customs MCP server (mcp_server/server.py).
  Each agent sees a filtered slice of its tools (least privilege), and every
  call is stamped with the calling agent's name so no agent can act as another.
- Deliberate routing: the boss sends each ticket to ONE specialist chosen by
  ticket type (ROUTING). That specialist may bring in others with
  `ask_teammate`, but only by naming a need (NEED_OWNER picks the agent), a
  specialist can be brought back at most once and only for a different need,
  helpers can't hand off further, and
  no ticket ever involves more than MAX_SPECIALISTS_PER_TICKET specialists.
  Handed-off runs are nested and share the ticket's token budget.
- Every agent run is recorded step by step in output/audit_trail.json.
"""

import os
import sys
import uuid
from dataclasses import replace
from pathlib import Path
from typing import Any

os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")

from dotenv import load_dotenv
from fastmcp import Client
from fastmcp.client.transports import StdioTransport
from pydantic_ai import Agent, FunctionToolset, ModelRequestNode, RunContext, RunUsage, UsageLimits
from pydantic_ai.mcp import CallToolFunc, MCPToolset
from pydantic_ai.models.openai import OpenAIResponsesModel, OpenAIResponsesModelSettings
from pydantic_ai.providers.openai import OpenAIProvider

import audit
import events
from models import (AGENT_NAMES, AgentName, AgentReport, AuditRecord, BossDecision, Handoff, HandoffNeed,
                    TeamDeps)

ROOT = Path(__file__).resolve().parent.parent
PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"
MCP_SERVER = ROOT / "mcp_server" / "server.py"

# The only model used anywhere in this project.
MODEL_NAME = "gpt-6-luna"
PORTKEY_BASE_URL = "https://api.portkey.ai/v1"

# ---- routing: who works a ticket ---------------------------------------------
# First (and only) specialist the boss may send each ticket type to.
ROUTING: dict[str, AgentName] = {
    "customer_order": "inventory",       # can we fill it? stock, shortfall, restock
    "rent_notice": "facilities",         # lease owner: verify amount and due date
    "price_override": "inventory",       # can we fill it before we price it?
}
# Every handoff names a need; the code, not the model, picks who owns it.
NEED_OWNER: dict[str, AgentName] = {
    "stock_or_vendor_check": "inventory",
    "payment_or_po_request": "accounting",
    "margin_or_cash_review": "accounting",
    "lease_or_rent_check": "facilities",
    "customer_draft": "customer_service",
}
# After the routed specialist reports, the boss may make ONE more handoff, only for these needs:
# a customer draft that reflects its decision, or a payment/PO the specialist reported but didn't file.
BOSS_FOLLOW_UP_NEEDS = {"customer_draft", "payment_or_po_request"}
MAX_BOSS_FOLLOW_UPS = 1
MAX_SPECIALISTS_PER_TICKET = 3     # never the whole team: at most 3 of the 4 specialists
MAX_VISITS_PER_SPECIALIST = 2      # a specialist can be brought back once, only for a different need

# ---- token guardrails (see output/harness.md, Safety) ------------------------
MAX_MODEL_REQUESTS_PER_AGENT = 8   # model round-trips in a single agent run
TICKET_USAGE_LIMITS = UsageLimits( # shared by every agent run inside one ticket run
    request_limit=40,
    tool_calls_limit=60,
    total_tokens_limit=300_000,
)
MODEL_SETTINGS = OpenAIResponsesModelSettings(
    max_tokens=2_000,
    timeout=45,                          # a hung gateway call is retried after 45s, not 90s
    openai_reasoning_effort="low",
    openai_reasoning_summary="concise",  # so the audit trail captures the model's reasoning
)

# Which MCP tools each role may call. Writes are narrow: only accounting files
# approvals; only customer_service and facilities post drafts. No agent can see
# human_decision_record (it isn't even registered on an agent-mode server).
AGENT_TOOLS: dict[AgentName, set[str]] = {
    "boss": {"desk_board_overview", "ticket_dossier_fetch", "cash_position_report", "status_note_update"},
    "inventory": {"ticket_dossier_fetch", "stock_margin_quote", "supplier_catalog_search",
                  "vendor_invoice_blockers", "status_note_update"},
    "accounting": {"ticket_dossier_fetch", "cash_position_report", "approval_request_file",
                   "vendor_invoice_blockers", "lease_rent_schedule", "stock_margin_quote", "status_note_update"},
    "facilities": {"ticket_dossier_fetch", "lease_rent_schedule", "cash_position_report",
                   "message_draft_post", "status_note_update"},
    "customer_service": {"ticket_dossier_fetch", "stock_margin_quote", "message_draft_post", "status_note_update"},
}
# Tool arguments that name the caller; always overwritten with the real caller.
IDENTITY_ARGS = {"status_note_update": "agent", "message_draft_post": "author", "approval_request_file": "requested_by"}


def _load_env() -> None:
    """The Portkey key lives in a .env outside the repo (hw5/, or up to two folders above)."""
    for folder in [ROOT, *ROOT.parents[:2]]:
        load_dotenv(folder / ".env")


_load_env()
_api_key = os.getenv("PORTKEY_API_KEY")
if not _api_key:
    raise RuntimeError("PORTKEY_API_KEY is missing. Copy .env.example to hw5/.env (or a folder above it) and fill it in.")
model = OpenAIResponsesModel(MODEL_NAME, provider=OpenAIProvider(api_key=_api_key, base_url=PORTKEY_BASE_URL))


# ---- MCP ---------------------------------------------------------------------

def mcp_transport() -> StdioTransport:
    """Agent-mode MCP server over stdio: no money-moving tool is registered."""
    return StdioTransport(command=sys.executable, args=[str(MCP_SERVER)],
                          env={"CAMPUS_MCP_ROLE": "agent"}, cwd=str(ROOT))


async def _stamp_identity(ctx: RunContext[TeamDeps], call_tool: CallToolFunc, name: str, args: dict[str, Any]):
    if name in IDENTITY_ARGS:
        args = {**args, IDENTITY_ARGS[name]: ctx.deps.agent}
    return await call_tool(name, args)


shop_mcp = MCPToolset(Client(mcp_transport()), process_tool_call=_stamp_identity, max_retries=2)


# ---- routing and handoffs ---------------------------------------------------

def _routing_snapshot(deps: TeamDeps) -> str:
    r = deps.routing
    trail = "; ".join(f"{h.from_agent}->{h.to_agent} ({h.need})" for h in r.handoffs) or "none yet"
    return f"Specialists on this ticket so far: {r.joined or 'none'}. Handoffs: {trail}."


async def _hand_off(ctx: RunContext[TeamDeps], to: AgentName, need: str, request: str, role: str) -> str:
    """Shared checks + nested run for route_ticket and ask_teammate."""
    d, r = ctx.deps, ctx.deps.routing
    earlier = [h for h in r.handoffs if h.to_agent == to]
    if earlier:
        # A specialist already on the ticket can be brought back once, for a different need
        # (e.g. accounting: margin review first, then a payment/PO request).
        if any(h.need == need for h in earlier):
            return f"Refused: {to} already handled '{need}' on ticket {d.ticket_id}. {_routing_snapshot(d)}"
        if len(earlier) >= MAX_VISITS_PER_SPECIALIST:
            return (f"Refused: {to} has already worked ticket {d.ticket_id} {MAX_VISITS_PER_SPECIALIST} times. "
                    f"Finish with what you have. {_routing_snapshot(d)}")
    elif len(r.joined) >= MAX_SPECIALISTS_PER_TICKET:
        return (f"Refused: ticket {d.ticket_id} already has {MAX_SPECIALISTS_PER_TICKET} specialists, the most "
                f"allowed. Finish with what you have. {_routing_snapshot(d)}")
    else:
        r.joined.append(to)
    r.handoffs.append(Handoff(from_agent=d.agent, to_agent=to, need=need, request=request))
    events.emit("handoff", ticket_id=d.ticket_id, ticket_run_id=d.ticket_run_id, agent=d.agent, role=d.role,
                from_agent=d.agent, to_agent=to, need=need, request=request)

    child = replace(d, agent=to, role=role, agent_run_id=uuid.uuid4().hex[:12], parent_run_id=d.agent_run_id,
                    chain=[*d.chain, to], depth=d.depth + 1)
    if role == "routed":
        tail = ("The boss routed this ticket to you as the first specialist. Work it in your lane. If a step "
                "belongs to another role, use ask_teammate with the matching need, only when you truly need it.")
    else:
        tail = "You were brought in as a helper for one need. Do just that; you can't hand off further."
    prompt = (f"Ticket {d.ticket_id} ({r.ticket_type}). From {d.agent}, need: {need}.\n{request}\n\n{tail} "
              "Return your AgentReport. Don't set the ticket's final status; the boss does that.")
    try:
        report = await run_agent(to, prompt, child, AgentReport, usage=ctx.usage)
    except StepLimitReached as e:
        return f"{to} stopped without a report: {e}"
    return report.model_dump_json()


async def _only_boss(ctx: RunContext[TeamDeps], tool_def):
    return tool_def if ctx.deps.role == "lead" else None


async def _boss_or_routed(ctx: RunContext[TeamDeps], tool_def):
    # Helpers never even see ask_teammate, so they can't fan work out further.
    return tool_def if ctx.deps.role in ("lead", "routed") else None


team_tools = FunctionToolset[TeamDeps]()


@team_tools.tool(prepare=_only_boss)
async def route_ticket(ctx: RunContext[TeamDeps], request: str) -> str:
    """Send this ticket to its ONE first specialist, chosen by ticket type
    (customer_order -> inventory, rent_notice -> facilities, price_override ->
    inventory). Call this once, early. Say exactly what you need back."""
    d, r = ctx.deps, ctx.deps.routing
    if r.routed_agent is None:
        return (f"Refused: ticket type '{r.ticket_type}' has no routing rule. Set the ticket to blocked with a note "
                "asking a human to route it.")
    if r.routed_agent in r.joined:
        return f"Refused: ticket {d.ticket_id} was already routed to {r.routed_agent}. {_routing_snapshot(d)}"
    return await _hand_off(ctx, r.routed_agent, "route", request, role="routed")


@team_tools.tool(prepare=_boss_or_routed)
async def ask_teammate(ctx: RunContext[TeamDeps], need: HandoffNeed, request: str) -> str:
    """Bring in another specialist for ONE need you can't cover in your own lane.
    The need decides who joins: stock_or_vendor_check -> inventory;
    payment_or_po_request and margin_or_cash_review -> accounting;
    lease_or_rent_check -> facilities; customer_draft -> customer_service.
    Put everything you need for that need in one self-contained request (ids,
    SKU/size/qty, amounts to check). A teammate can be brought back once more,
    but only for a different need (e.g. margin review, then a payment/PO request)."""
    d, r = ctx.deps, ctx.deps.routing
    to = NEED_OWNER[need]
    if to == d.agent:
        return f"Refused: {need} is your own job. Do it with your tools."
    if d.role == "lead":
        if r.routed_agent not in r.joined:
            return f"Refused: route the ticket first (route_ticket goes to {r.routed_agent})."
        if need not in BOSS_FOLLOW_UP_NEEDS:
            return (f"Refused: after routing, the boss may only bring in {sorted(BOSS_FOLLOW_UP_NEEDS)}. "
                    f"The routed specialist ({r.routed_agent}) handles other handoffs.")
        if sum(h.from_agent == "boss" and h.need != "route" for h in r.handoffs) >= MAX_BOSS_FOLLOW_UPS:
            return f"Refused: the boss gets {MAX_BOSS_FOLLOW_UPS} follow-up handoff after routing, and it's used. {_routing_snapshot(d)}"
    return await _hand_off(ctx, to, need, request, role="helper")


# ---- agents ------------------------------------------------------------------

def _build(name: AgentName) -> Agent[TeamDeps, Any]:
    allowed = AGENT_TOOLS[name]
    return Agent(
        model,
        name=name,
        deps_type=TeamDeps,
        instructions=(PROMPTS_DIR / f"{name}.md").read_text(),
        toolsets=[shop_mcp.filtered(lambda ctx, tool_def: tool_def.name in allowed), team_tools],
        model_settings=MODEL_SETTINGS,
        retries=2,
    )


AGENTS: dict[AgentName, Agent[TeamDeps, Any]] = {name: _build(name) for name in AGENT_NAMES}


class StepLimitReached(Exception):
    pass


async def run_agent(name: AgentName, prompt: str, deps: TeamDeps, output_type: type,
                    usage: RunUsage) -> AgentReport | BossDecision:
    """Run one agent through its loop, recording every step to the audit trail."""
    record = AuditRecord(
        record_type="agent_run", ticket_run_id=deps.ticket_run_id, agent_run_id=deps.agent_run_id,
        parent_run_id=deps.parent_run_id, ticket_id=deps.ticket_id, agent=name, model=MODEL_NAME,
        role=deps.role, depth=deps.depth, chain=list(deps.chain), started_at=audit.now(), finished_at="", status="ok", prompt=prompt,
    )
    usage_before = RunUsage(**{k: getattr(usage, k) for k in ("requests", "tool_calls", "input_tokens", "output_tokens")})
    model_requests = 0
    who = {"ticket_id": deps.ticket_id, "ticket_run_id": deps.ticket_run_id, "agent": name, "role": deps.role,
           "agent_run_id": deps.agent_run_id}
    events.emit("agent_started", parent_run_id=deps.parent_run_id, **who)
    try:
        async with AGENTS[name].iter(prompt, deps=deps, output_type=output_type, usage=usage,
                                     usage_limits=TICKET_USAGE_LIMITS) as run:
            async for node in run:
                step = audit.step_from_node(len(record.steps) + 1, node)
                if step:
                    record.steps.append(step)
                    events.emit_step(step, **who)
                if isinstance(node, ModelRequestNode):
                    model_requests += 1
                    if model_requests > MAX_MODEL_REQUESTS_PER_AGENT:
                        raise StepLimitReached(f"{name} hit {MAX_MODEL_REQUESTS_PER_AGENT} model requests")
        output = run.result.output
        record.output = output.model_dump(mode="json")
        record.steps.append(audit.AuditStep(step=len(record.steps) + 1, node="end", at=audit.now(),
                                            parts=[{"output": record.output}]))
        return output
    except StepLimitReached as e:
        record.status, record.error = "stopped", str(e)
        raise
    except Exception as e:
        record.status, record.error = "error", f"{type(e).__name__}: {e}"
        raise
    finally:
        record.finished_at = audit.now()
        record.usage = {
            "requests": usage.requests - usage_before.requests,
            "tool_calls": usage.tool_calls - usage_before.tool_calls,
            "input_tokens": usage.input_tokens - usage_before.input_tokens,
            "output_tokens": usage.output_tokens - usage_before.output_tokens,
            "note": "includes any specialist runs this agent handed off to",
        }
        audit.append(record)
        events.emit("agent_finished", status=record.status, output=record.output, error=record.error, **who)
