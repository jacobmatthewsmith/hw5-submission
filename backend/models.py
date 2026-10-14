"""Data types shared by the Campus Customs agent team.

Shop facts never live here: every number an agent reports comes from an MCP
tool call over data/campus_customs_new.db. These types only shape what agents
hand back to each other and what gets written to output/audit_trail.json.
"""

from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import BaseModel, Field

AgentName = Literal["boss", "inventory", "accounting", "facilities", "customer_service"]
AGENT_NAMES: tuple[AgentName, ...] = ("boss", "inventory", "accounting", "facilities", "customer_service")

TicketStatus = Literal["open", "in_progress", "waiting_on_approval", "blocked", "resolved"]


# ---------------------------------------------------------------- agent outputs

class Finding(BaseModel):
    """One fact an agent relies on, tied to the MCP tool that returned it."""

    fact: str = Field(description="A single fact, with the exact numbers/dates the tool returned.")
    source_tool: str = Field(description="Name of the MCP tool call this fact came from.")


class AgentReport(BaseModel):
    """What a specialist (inventory, accounting, facilities, customer_service) hands back."""

    agent: AgentName
    ticket_id: int
    summary: str = Field(description="One or two plain-English sentences a shop owner can skim: what you found and did.")
    technical_summary: str = Field(
        description="Two to four sentences for an auditor: the MCP tools you called (by name) with the key numbers "
                    "they returned, any handoff you made (need and to whom), and every approval/draft id you created.")
    findings: list[Finding] = Field(default_factory=list)
    actions_taken: list[str] = Field(
        default_factory=list, description="Writes you made via MCP tools (approval requests, drafts, status notes).")
    approval_ids: list[int] = Field(default_factory=list, description="Approval requests you filed (pending a human).")
    draft_ids: list[int] = Field(default_factory=list, description="Message drafts you saved on the board.")
    blockers: list[str] = Field(default_factory=list, description="Anything stopping this ticket from moving forward.")
    recommended_next_step: str


class BossDecision(BaseModel):
    """The boss's final call on a ticket, at the end of a ticket run."""

    ticket_id: int
    final_status: TicketStatus
    headline: str = Field(description="Three to six words for the scoreboard, e.g. 'Rent queued for approval'.")
    decision: str = Field(description="The call you made, in one or two plain-English sentences.")
    technical_summary: str = Field(
        description="Two to four sentences for an auditor: who you routed to and why, the MCP tools you called with "
                    "key numbers, the approval and draft ids involved, and the status you set.")
    rationale: str = Field(description="Why, citing the specialist findings and tool numbers it rests on.")
    agents_consulted: list[AgentName] = Field(default_factory=list)
    waiting_on_human: list[int] = Field(
        default_factory=list, description="Approval ids a human must approve or reject before this can close.")
    draft_ids: list[int] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------- run context

# Why one agent hands work to another. Each need has exactly one owning agent
# (see NEED_OWNER in agents.py), so a handoff names the need and the code picks
# the agent; nobody can "cc everyone".
HandoffNeed = Literal[
    "stock_or_vendor_check",    # -> inventory
    "payment_or_po_request",    # -> accounting (only role that files approvals)
    "margin_or_cash_review",    # -> accounting
    "lease_or_rent_check",      # -> facilities
    "customer_draft",           # -> customer_service
]

# lead = the boss; routed = the one specialist the ticket type sends it to;
# helper = a specialist the routed agent (or boss, for a customer draft) brought in.
TicketRole = Literal["lead", "routed", "helper"]


@dataclass
class Handoff:
    from_agent: AgentName
    to_agent: AgentName
    need: str
    request: str


@dataclass
class TicketRouting:
    """Shared by every agent run inside one ticket run: who's been brought in, and why."""

    ticket_type: str
    routed_agent: AgentName | None          # first specialist for this ticket type (None = unknown type)
    joined: list[AgentName] = field(default_factory=list)      # specialists who have worked this ticket
    handoffs: list[Handoff] = field(default_factory=list)


@dataclass
class TeamDeps:
    """Passed to every agent run. A handed-off run gets a child copy (depth + 1)."""

    ticket_id: int
    ticket_run_id: str
    agent: AgentName
    role: TicketRole
    agent_run_id: str
    chain: list[AgentName]
    depth: int
    routing: TicketRouting
    parent_run_id: str | None = None


# ---------------------------------------------------------------- audit trail

class AuditStep(BaseModel):
    """One step of the agent loop (a node in the PydanticAI agent graph)."""

    step: int
    node: str = Field(description="user_prompt | model_request | model_response | end")
    at: str
    parts: list[dict[str, Any]] = Field(default_factory=list)


class AuditRecord(BaseModel):
    """One entry in output/audit_trail.json: an agent run, a ticket run, a human
    approve/reject decision, a database reset, or a replay that restored the
    working DB from earlier audit records (no model calls)."""

    record_type: Literal["agent_run", "ticket_run", "human_decision", "db_reset", "db_replay"]
    ticket_run_id: str | None = None
    agent_run_id: str | None = None
    parent_run_id: str | None = None
    ticket_id: int | None = None
    agent: AgentName | Literal["team", "human"]
    model: str | None = Field(default=None, description="None for human decisions and resets (no model involved).")
    role: TicketRole | None = None
    depth: int = 0
    chain: list[str] = Field(default_factory=list)
    started_at: str
    finished_at: str
    status: Literal["ok", "error", "stopped"]
    prompt: str | None = None
    steps: list[AuditStep] = Field(default_factory=list)
    output: dict[str, Any] | None = None
    error: str | None = None
    usage: dict[str, Any] = Field(default_factory=dict)
    routing: dict[str, Any] | None = Field(
        default=None, description="ticket_run only: ticket type, first specialist, who joined, every handoff and why.")
