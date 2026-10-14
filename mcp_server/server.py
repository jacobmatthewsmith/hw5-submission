"""Campus Customs MCP server.

Exposes the shop database to the agent team as MCP tools. Every tool reads
and writes the working copy, data/campus_customs_new.db. The original
data/campus_customs.db is never opened here, so it stays a clean reset point.

Tools only report what is in the database plus simple arithmetic on those
values (days between dates, margins, totals). They never fill in missing data:
if a row isn't there, the tool raises an error instead of guessing. Money
amounts on approval requests are always computed from the database, never
taken from the caller.

Roles: the server starts in "agent" mode unless CAMPUS_MCP_ROLE=human. Agent
mode can file approval requests but cannot approve or pay anything. Only a
human-mode server (used by the backend's approval endpoint) registers
human_decision_record, the one tool that moves money.
"""

import os
import sqlite3
from calendar import monthrange
from contextlib import contextmanager
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Literal

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "campus_customs_new.db"
MCP_ROLE = os.getenv("CAMPUS_MCP_ROLE", "agent")

AGENTS = {"boss", "inventory", "accounting", "facilities", "customer_service"}
TICKET_STATUSES = ("open", "in_progress", "waiting_on_approval", "blocked", "resolved")

mcp = FastMCP(
    name="campus-customs",
    instructions=(
        "Tools for the Campus Customs shop database. 'Today' is desk.date_today, "
        "not the real clock. Only report values these tools return; never invent data. "
        "Payments and purchase orders can only be requested here; a human approves them."
    ),
)

# Board-state tables the original database doesn't have. Created only in the
# working copy, so resetting from the original wipes them too.
_EXTRA_SCHEMA = """
CREATE TABLE IF NOT EXISTS approvals (
    id INTEGER PRIMARY KEY,
    ticket_id INTEGER NOT NULL REFERENCES tickets(id),
    kind TEXT NOT NULL CHECK (kind IN ('invoice_payment', 'rent_payment', 'purchase_order')),
    ref_id INTEGER,
    vendor_id INTEGER REFERENCES vendors(id),
    sku TEXT,
    size TEXT,
    qty INTEGER,
    amount REAL NOT NULL,
    account TEXT NOT NULL,
    reason TEXT NOT NULL,
    requested_by TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'executed', 'rejected')),
    decided_by TEXT,
    decided_at TEXT,
    result_note TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS drafts (
    id INTEGER PRIMARY KEY,
    ticket_id INTEGER NOT NULL REFERENCES tickets(id),
    author TEXT NOT NULL,
    recipient TEXT NOT NULL,
    subject TEXT NOT NULL,
    body TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft' CHECK (status = 'draft'),
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS ticket_log (
    id INTEGER PRIMARY KEY,
    ticket_id INTEGER NOT NULL REFERENCES tickets(id),
    agent TEXT NOT NULL,
    status TEXT NOT NULL,
    note TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


@contextmanager
def _connect():
    # sqlite3.connect would silently create an empty file, so check first.
    if not DB_PATH.exists():
        raise ToolError(f"Working database not found at {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        conn.executescript(_EXTRA_SCHEMA)
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _shop_today(conn: sqlite3.Connection) -> date:
    row = conn.execute("SELECT date_today FROM desk").fetchone()
    if row is None:
        raise ToolError("desk table has no date_today row")
    return date.fromisoformat(row["date_today"])


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _add_month(d: date) -> date:
    year, month = (d.year + 1, 1) if d.month == 12 else (d.year, d.month + 1)
    return date(year, month, min(d.day, monthrange(year, month)[1]))


def _row(conn: sqlite3.Connection, sql: str, params: tuple, missing: str) -> sqlite3.Row:
    row = conn.execute(sql, params).fetchone()
    if row is None:
        raise ToolError(missing)
    return row


def _open_invoices(conn: sqlite3.Connection, vendor_id: int) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM invoices WHERE vendor_id = ? AND status = 'open' ORDER BY due_date", (vendor_id,)
    ).fetchall()


def _pending_payment_total(conn: sqlite3.Connection, account: str) -> float:
    row = conn.execute(
        "SELECT COALESCE(SUM(amount), 0) AS total FROM approvals "
        "WHERE status = 'pending' AND kind != 'purchase_order' AND account = ?",
        (account,),
    ).fetchone()
    return round(row["total"], 2)


def _check_agent(agent: str) -> None:
    if agent not in AGENTS:
        raise ToolError(f"Unknown agent '{agent}'. Expected one of {sorted(AGENTS)}")


# ---------------------------------------------------------------- board

@mcp.tool
def desk_board_overview(status: str | None = None) -> dict:
    """List tickets on the board along with the shop's 'today'.

    With no status, returns every ticket; pass a status (open, in_progress,
    waiting_on_approval, blocked, resolved) to filter. Start here to see what
    needs work.

    Reads: desk, tickets.
    """
    if status is not None and status not in TICKET_STATUSES:
        raise ToolError(f"status must be one of {TICKET_STATUSES}")
    with _connect() as conn:
        today = _shop_today(conn)
        desk_notes = conn.execute("SELECT notes FROM desk").fetchone()["notes"]
        sql = "SELECT id, type, requester, subject, status, created_at FROM tickets"
        rows = conn.execute(sql + (" WHERE status = ?" if status else "") + " ORDER BY id",
                            (status,) if status else ()).fetchall()
    return {
        "shop_today": today.isoformat(),
        "desk_notes": desk_notes,
        "tickets": [dict(r) for r in rows],
    }


@mcp.tool
def ticket_dossier_fetch(ticket_id: int) -> dict:
    """Open one ticket with everything it links to.

    Returns the ticket row, the linked inventory and pricing (if it names a
    SKU), lease (if lease_id), invoice and its vendor (if invoice_id), plus any
    approval requests, drafts, and agent notes already filed for it.

    Reads: tickets, desk, inventory, pricing, leases, invoices, vendors,
    approvals, drafts, ticket_log.
    """
    with _connect() as conn:
        today = _shop_today(conn)
        t = _row(conn, "SELECT * FROM tickets WHERE id = ?", (ticket_id,), f"No ticket with id {ticket_id}")
        dossier: dict = {"shop_today": today.isoformat(), "ticket": dict(t)}

        if t["sku"]:
            dossier["inventory"] = [dict(r) for r in conn.execute(
                "SELECT size, qty, location FROM inventory WHERE sku = ? ORDER BY rowid", (t["sku"],))]
            price = conn.execute("SELECT unit_cost, list_price FROM pricing WHERE sku = ?", (t["sku"],)).fetchone()
            dossier["pricing"] = dict(price) if price else None
        if t["lease_id"] is not None:
            lease = conn.execute("SELECT * FROM leases WHERE id = ?", (t["lease_id"],)).fetchone()
            dossier["lease"] = dict(lease) if lease else None
        if t["invoice_id"] is not None:
            inv = conn.execute("SELECT * FROM invoices WHERE id = ?", (t["invoice_id"],)).fetchone()
            dossier["invoice"] = dict(inv) if inv else None
            if inv:
                vendor = conn.execute("SELECT * FROM vendors WHERE id = ?", (inv["vendor_id"],)).fetchone()
                dossier["invoice_vendor"] = dict(vendor) if vendor else None

        for key, table in (("approvals", "approvals"), ("drafts", "drafts"), ("agent_notes", "ticket_log")):
            dossier[key] = [dict(r) for r in conn.execute(
                f"SELECT * FROM {table} WHERE ticket_id = ? ORDER BY id", (ticket_id,))]
    return dossier


@mcp.tool
def status_note_update(ticket_id: int, agent: str, status: str, note: str) -> dict:
    """Set a ticket's status and log a note explaining why.

    agent is who is writing (boss, inventory, accounting, facilities,
    customer_service). status is one of open, in_progress, waiting_on_approval,
    blocked, resolved. Only the boss may set 'resolved', and not while the
    ticket still has a pending approval request. The ticket's original notes
    are never overwritten; the note goes to ticket_log.

    Reads/writes: tickets, ticket_log. Reads: approvals.
    """
    _check_agent(agent)
    if status not in TICKET_STATUSES:
        raise ToolError(f"status must be one of {TICKET_STATUSES}")
    if not note.strip():
        raise ToolError("note must explain the status change")
    with _connect() as conn:
        t = _row(conn, "SELECT status FROM tickets WHERE id = ?", (ticket_id,), f"No ticket with id {ticket_id}")
        if status == "resolved":
            if agent != "boss":
                raise ToolError("Only the boss can resolve a ticket")
            pending = conn.execute(
                "SELECT id FROM approvals WHERE ticket_id = ? AND status = 'pending'", (ticket_id,)).fetchall()
            if pending:
                raise ToolError(f"Ticket {ticket_id} has pending approvals {[r['id'] for r in pending]}; "
                                "use waiting_on_approval until a human decides")
        conn.execute("UPDATE tickets SET status = ? WHERE id = ?", (status, ticket_id))
        cur = conn.execute(
            "INSERT INTO ticket_log (ticket_id, agent, status, note, created_at) VALUES (?, ?, ?, ?, ?)",
            (ticket_id, agent, status, note.strip(), _now()))
    return {"ticket_id": ticket_id, "previous_status": t["status"], "status": status, "log_id": cur.lastrowid}


# ---------------------------------------------------------------- inventory

@mcp.tool
def stock_margin_quote(sku: str, size: str, qty: int, discount_pct: float | None = None) -> dict:
    """Check stock for a SKU and size against a requested quantity, and price it.

    Returns on-hand stock for every size of the SKU, the shortfall for the
    requested size, the cost to restock that shortfall at unit_cost, and the
    margin at list price. If discount_pct is given (0-100), also returns the
    discounted unit price and margin so a discount can be judged against cost.

    Reads: inventory, pricing.
    """
    if qty <= 0:
        raise ToolError("qty must be positive")
    if discount_pct is not None and not 0 <= discount_pct <= 100:
        raise ToolError("discount_pct must be between 0 and 100")

    with _connect() as conn:
        stock_rows = conn.execute(
            "SELECT * FROM inventory WHERE sku = ? ORDER BY rowid", (sku,)
        ).fetchall()
        price = conn.execute("SELECT * FROM pricing WHERE sku = ?", (sku,)).fetchone()

    if not stock_rows:
        raise ToolError(f"No inventory rows for sku {sku}")
    if price is None:
        raise ToolError(f"No pricing row for sku {sku}")

    by_size = {r["size"]: r for r in stock_rows}
    if size not in by_size:
        raise ToolError(f"sku {sku} has no size {size}; sizes on file: {sorted(by_size)}")

    on_hand = by_size[size]["qty"]
    shortfall = max(qty - on_hand, 0)
    unit_cost = price["unit_cost"]
    list_price = price["list_price"]

    def margin_block(unit_price: float) -> dict:
        unit_margin = unit_price - unit_cost
        return {
            "unit_price": round(unit_price, 2),
            "unit_margin": round(unit_margin, 2),
            "margin_pct": round(unit_margin / unit_price * 100, 1) if unit_price else None,
            "order_revenue": round(unit_price * qty, 2),
            "order_margin": round(unit_margin * qty, 2),
            "below_cost": unit_price < unit_cost,
        }

    result = {
        "sku": sku,
        "name": by_size[size]["name"],
        "location": by_size[size]["location"],
        "requested": {"size": size, "qty": qty},
        "stock_by_size": {r["size"]: r["qty"] for r in stock_rows},
        "on_hand": on_hand,
        "shortfall": shortfall,
        "unit_cost": unit_cost,
        "list_price": list_price,
        "restock_cost_for_shortfall": round(shortfall * unit_cost, 2),
        "at_list_price": margin_block(list_price),
    }
    if discount_pct is not None:
        result["at_discount"] = {"discount_pct": discount_pct, **margin_block(list_price * (1 - discount_pct / 100))}
    return result


@mcp.tool
def supplier_catalog_search(specialty_keyword: str | None = None) -> dict:
    """List vendors (optionally filtered by a word in their specialty) with lead
    times and whether each can ship right now.

    A vendor cannot ship while it has any open invoice. Use this to pick a
    restock vendor; use vendor_invoice_blockers for one vendor's invoice detail.

    Reads: vendors, invoices, desk.
    """
    with _connect() as conn:
        today = _shop_today(conn)
        sql = "SELECT * FROM vendors"
        rows = conn.execute(sql + (" WHERE specialty LIKE ?" if specialty_keyword else "") + " ORDER BY id",
                            (f"%{specialty_keyword}%",) if specialty_keyword else ()).fetchall()
        vendors = []
        for v in rows:
            open_inv = _open_invoices(conn, v["id"])
            vendors.append({
                **dict(v),
                "open_invoice_ids": [i["id"] for i in open_inv],
                "can_ship": not open_inv,
                "arrival_if_ordered_today": date.fromordinal(today.toordinal() + v["lead_days"]).isoformat(),
            })
    return {"shop_today": today.isoformat(), "vendors": vendors}


@mcp.tool
def vendor_invoice_blockers(invoice_id: int | None = None, vendor_id: int | None = None) -> dict:
    """Check whether a vendor is blocked from shipping by an open unpaid invoice.

    Pass an invoice_id (e.g. from tickets.invoice_id) or a vendor_id. Returns the
    vendor, its lead time, every open invoice it has with days overdue relative to
    desk.date_today, and whether it can ship. A vendor will not ship new product
    while it has any open invoice.

    Reads: invoices, vendors, desk.
    """
    if invoice_id is None and vendor_id is None:
        raise ToolError("Provide invoice_id or vendor_id")

    with _connect() as conn:
        today = _shop_today(conn)

        if invoice_id is not None:
            inv = _row(conn, "SELECT vendor_id FROM invoices WHERE id = ?", (invoice_id,),
                       f"No invoice with id {invoice_id}")
            if vendor_id is not None and vendor_id != inv["vendor_id"]:
                raise ToolError(f"Invoice {invoice_id} belongs to vendor {inv['vendor_id']}, not {vendor_id}")
            vendor_id = inv["vendor_id"]

        vendor = _row(conn, "SELECT * FROM vendors WHERE id = ?", (vendor_id,), f"No vendor with id {vendor_id}")
        open_rows = _open_invoices(conn, vendor_id)

    open_invoices = []
    for r in open_rows:
        days_overdue = (today - date.fromisoformat(r["due_date"])).days
        open_invoices.append({
            "invoice_id": r["id"],
            "amount": r["amount"],
            "due_date": r["due_date"],
            "description": r["description"],
            "days_overdue": max(days_overdue, 0),
            "is_overdue": days_overdue > 0,
        })

    return {
        "shop_today": today.isoformat(),
        "vendor": {
            "id": vendor["id"],
            "name": vendor["name"],
            "specialty": vendor["specialty"],
            "lead_days": vendor["lead_days"],
        },
        "open_invoices": open_invoices,
        "open_total": round(sum(i["amount"] for i in open_invoices), 2),
        "can_ship": not open_invoices,
    }


# ---------------------------------------------------------------- facilities

@mcp.tool
def lease_rent_schedule(lease_id: int) -> dict:
    """Look up a lease's rent amount and due date, and whether cash covers it.

    Returns the lease, days until rent is due relative to desk.date_today
    (negative means overdue), and each cash account's balance with whether it
    can cover one month's rent without going negative.

    Reads: leases, cash_accounts, desk.
    """
    with _connect() as conn:
        today = _shop_today(conn)
        lease = _row(conn, "SELECT * FROM leases WHERE id = ?", (lease_id,), f"No lease with id {lease_id}")
        accounts = conn.execute("SELECT * FROM cash_accounts ORDER BY name").fetchall()

    rent = lease["monthly_rent"]
    days_until_due = (date.fromisoformat(lease["next_due"]) - today).days

    return {
        "shop_today": today.isoformat(),
        "lease": {
            "id": lease["id"],
            "space_name": lease["space_name"],
            "landlord": lease["landlord"],
            "monthly_rent": rent,
            "next_due": lease["next_due"],
            "notes": lease["notes"],
        },
        "days_until_due": days_until_due,
        "is_overdue": days_until_due < 0,
        "cash_accounts": [
            {
                "name": a["name"],
                "balance": a["balance"],
                "balance_date": a["date"],
                "covers_rent": a["balance"] >= rent,
                "balance_after_rent": round(a["balance"] - rent, 2),
            }
            for a in accounts
        ],
    }


# ---------------------------------------------------------------- accounting

@mcp.tool
def cash_position_report() -> dict:
    """Show cash on hand, money already committed to pending approvals, every
    open invoice, and payments made so far.

    'available_after_pending' is what would be left if every pending payment
    request were approved. Purchase orders don't move cash in this model.

    Reads: cash_accounts, approvals, invoices, vendors, payments, desk.
    """
    with _connect() as conn:
        today = _shop_today(conn)
        accounts = []
        for a in conn.execute("SELECT * FROM cash_accounts ORDER BY name"):
            pending = _pending_payment_total(conn, a["name"])
            accounts.append({
                "name": a["name"],
                "balance": a["balance"],
                "balance_date": a["date"],
                "pending_payment_requests": pending,
                "available_after_pending": round(a["balance"] - pending, 2),
            })
        invoices = []
        for r in conn.execute(
            "SELECT i.*, v.name AS vendor_name FROM invoices i JOIN vendors v ON v.id = i.vendor_id "
            "WHERE i.status = 'open' ORDER BY i.due_date"
        ):
            days_overdue = (today - date.fromisoformat(r["due_date"])).days
            invoices.append({**dict(r), "days_overdue": max(days_overdue, 0), "is_overdue": days_overdue > 0})
        pending_approvals = [dict(r) for r in conn.execute(
            "SELECT id, ticket_id, kind, ref_id, vendor_id, sku, size, qty, amount, account, requested_by, reason, result_note "
            "FROM approvals WHERE status = 'pending' ORDER BY id")]
        payments = [dict(r) for r in conn.execute("SELECT * FROM payments ORDER BY id")]
    return {
        "shop_today": today.isoformat(),
        "cash_accounts": accounts,
        "open_invoices": invoices,
        "pending_approvals": pending_approvals,
        "payments": payments,
    }


@mcp.tool
def approval_request_file(
    ticket_id: int,
    kind: Literal["invoice_payment", "rent_payment", "purchase_order"],
    requested_by: str,
    reason: str,
    invoice_id: int | None = None,
    lease_id: int | None = None,
    vendor_id: int | None = None,
    sku: str | None = None,
    size: str | None = None,
    qty: int | None = None,
    account: str = "checking",
) -> dict:
    """Queue a payment or purchase order for HUMAN approval. Nothing is paid here.

    Only accounting may file. The amount always comes from the database:
      - invoice_payment: needs invoice_id; amount = invoices.amount (invoice must be open).
      - rent_payment: needs lease_id; amount = leases.monthly_rent.
      - purchase_order: needs vendor_id, sku, size, qty; amount = qty * pricing.unit_cost.
    Refuses duplicates of something already pending. Returns the request plus a
    cash check and, for purchase orders, whether the vendor is blocked by an
    open invoice (a blocked PO cannot be executed until that invoice is paid).

    Writes: approvals. Reads: tickets, invoices, leases, vendors, inventory,
    pricing, cash_accounts.
    """
    if requested_by != "accounting":
        raise ToolError("Only accounting can file payment or purchase order requests; delegate to accounting")
    if not reason.strip():
        raise ToolError("reason is required")

    with _connect() as conn:
        _row(conn, "SELECT id FROM tickets WHERE id = ?", (ticket_id,), f"No ticket with id {ticket_id}")
        acct = _row(conn, "SELECT * FROM cash_accounts WHERE name = ?", (account,), f"No cash account '{account}'")
        ref_id = None
        blockers: list[int] = []

        if kind == "invoice_payment":
            if invoice_id is None:
                raise ToolError("invoice_payment needs invoice_id")
            inv = _row(conn, "SELECT * FROM invoices WHERE id = ?", (invoice_id,), f"No invoice with id {invoice_id}")
            if inv["status"] != "open":
                raise ToolError(f"Invoice {invoice_id} is '{inv['status']}', not open")
            ref_id, vendor_id, amount = invoice_id, inv["vendor_id"], inv["amount"]
            dup_sql, dup_args = "kind = 'invoice_payment' AND ref_id = ?", (invoice_id,)

        elif kind == "rent_payment":
            if lease_id is None:
                raise ToolError("rent_payment needs lease_id")
            lease = _row(conn, "SELECT * FROM leases WHERE id = ?", (lease_id,), f"No lease with id {lease_id}")
            ref_id, amount = lease_id, lease["monthly_rent"]
            dup_sql, dup_args = "kind = 'rent_payment' AND ref_id = ?", (lease_id,)

        else:
            if vendor_id is None or not sku or not size or not qty or qty <= 0:
                raise ToolError("purchase_order needs vendor_id, sku, size and a positive qty")
            _row(conn, "SELECT id FROM vendors WHERE id = ?", (vendor_id,), f"No vendor with id {vendor_id}")
            _row(conn, "SELECT qty FROM inventory WHERE sku = ? AND size = ?", (sku, size),
                 f"No inventory row for {sku} size {size}")
            price = _row(conn, "SELECT unit_cost FROM pricing WHERE sku = ?", (sku,), f"No pricing for {sku}")
            amount = round(qty * price["unit_cost"], 2)
            blockers = [i["id"] for i in _open_invoices(conn, vendor_id)]
            dup_sql, dup_args = "kind = 'purchase_order' AND vendor_id = ? AND sku = ? AND size = ?", (vendor_id, sku, size)

        dup = conn.execute(f"SELECT id FROM approvals WHERE status = 'pending' AND {dup_sql}", dup_args).fetchone()
        if dup:
            raise ToolError(f"Approval {dup['id']} is already pending for this; don't file it twice")

        cur = conn.execute(
            "INSERT INTO approvals (ticket_id, kind, ref_id, vendor_id, sku, size, qty, amount, account, "
            "reason, requested_by, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (ticket_id, kind, ref_id, vendor_id, sku, size, qty, amount, account, reason.strip(),
             requested_by, _now()))
        pending_total = _pending_payment_total(conn, account)

    result = {
        "approval_id": cur.lastrowid,
        "status": "pending",
        "kind": kind,
        "amount": amount,
        "account": account,
        "note": "Queued for human approval. No money has moved.",
        "cash_check": {
            "balance": acct["balance"],
            "pending_payment_requests_incl_this": pending_total,
            "covers_all_pending": acct["balance"] >= pending_total,
        },
    }
    if kind == "purchase_order":
        result["vendor_blocked_by_open_invoices"] = blockers
    return result


# ---------------------------------------------------------------- customer service

@mcp.tool
def message_draft_post(ticket_id: int, author: str, recipient: str, subject: str, body: str) -> dict:
    """Save a message as a DRAFT on the board for a human to review. It is never sent.

    Use for customer replies and any vendor or landlord correspondence. There is
    no send tool: drafts stay on the board.

    Writes: drafts. Reads: tickets.
    """
    _check_agent(author)
    if not (recipient.strip() and subject.strip() and body.strip()):
        raise ToolError("recipient, subject and body are all required")
    with _connect() as conn:
        _row(conn, "SELECT id FROM tickets WHERE id = ?", (ticket_id,), f"No ticket with id {ticket_id}")
        cur = conn.execute(
            "INSERT INTO drafts (ticket_id, author, recipient, subject, body, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (ticket_id, author, recipient.strip(), subject.strip(), body.strip(), _now()))
    return {"draft_id": cur.lastrowid, "status": "draft", "sent": False}


# ---------------------------------------------------------------- human only

def _settle_ticket(conn: sqlite3.Connection, ticket_id: int, approver: str) -> None:
    """A ticket parked in waiting_on_approval only needed a human. Once nothing is
    pending, close it: resolved if every request was carried out, blocked (for a
    follow-up run) if the human rejected any of them."""
    t = conn.execute("SELECT status FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
    if t is None or t["status"] != "waiting_on_approval":
        return
    rows = conn.execute("SELECT id, status FROM approvals WHERE ticket_id = ?", (ticket_id,)).fetchall()
    if any(r["status"] == "pending" for r in rows):
        return
    rejected = [r["id"] for r in rows if r["status"] == "rejected"]
    status, note = (("blocked", f"Human rejected approval(s) {rejected}; ticket needs a follow-up run.") if rejected
                    else ("resolved", "All approval requests decided and carried out by a human."))
    conn.execute("UPDATE tickets SET status = ? WHERE id = ?", (status, ticket_id))
    conn.execute("INSERT INTO ticket_log (ticket_id, agent, status, note, created_at) VALUES (?, ?, ?, ?, ?)",
                 (ticket_id, f"human:{approver}", status, note, _now()))

def human_decision_record(approval_id: int, decision: Literal["approve", "reject"], approver: str,
                          comment: str | None = None) -> dict:
    """HUMAN ONLY. Approve or reject a pending approval request.

    Approving a payment pays it: checks the balance (refuses if it would go
    negative, leaving the request pending), writes a payments row with the
    approver's name, lowers cash_accounts.balance, and marks the invoice paid or
    moves the lease's next_due forward one month. Approving a purchase order
    places it, unless the vendor still has an open invoice (then it refuses and
    stays pending). Rejecting closes the request with no money moved.

    Writes: approvals, payments, cash_accounts, invoices, leases, ticket_log.
    Reads: desk, vendors.
    """
    if MCP_ROLE != "human":
        raise ToolError("human_decision_record is only available to a human-mode server")
    approver = approver.strip()
    if not approver or approver.lower() in AGENTS:
        raise ToolError("approver must be the name of the human approving, not an agent")

    with _connect() as conn:
        today = _shop_today(conn)
        a = _row(conn, "SELECT * FROM approvals WHERE id = ?", (approval_id,), f"No approval with id {approval_id}")
        if a["status"] != "pending":
            raise ToolError(f"Approval {approval_id} is already '{a['status']}'")

        def close(status: str, note: str) -> dict:
            conn.execute("UPDATE approvals SET status = ?, decided_by = ?, decided_at = ?, result_note = ? WHERE id = ?",
                         (status, approver, _now(), note, approval_id))
            conn.execute("INSERT INTO ticket_log (ticket_id, agent, status, note, created_at) "
                         "SELECT ?, ?, status, ?, ? FROM tickets WHERE id = ?",
                         (a["ticket_id"], f"human:{approver}", f"Approval {approval_id}: {note}", _now(), a["ticket_id"]))
            _settle_ticket(conn, a["ticket_id"], approver)
            return {"approval_id": approval_id, "ticket_id": a["ticket_id"], "kind": a["kind"],
                    "status": status, "note": note}

        def refuse(note: str) -> dict:
            conn.execute("UPDATE approvals SET result_note = ? WHERE id = ?", (f"REFUSED: {note}", approval_id))
            return {"approval_id": approval_id, "ticket_id": a["ticket_id"], "kind": a["kind"],
                    "status": "pending", "executed": False, "refused": note}

        if decision == "reject":
            return close("rejected", f"Rejected by {approver}" + (f": {comment}" if comment else ""))

        if a["kind"] == "purchase_order":
            blockers = [i["id"] for i in _open_invoices(conn, a["vendor_id"])]
            if blockers:
                return refuse(f"vendor {a['vendor_id']} still has open invoice(s) {blockers}; pay them first")
            vendor = _row(conn, "SELECT * FROM vendors WHERE id = ?", (a["vendor_id"],), "Vendor missing")
            arrival = date.fromordinal(today.toordinal() + vendor["lead_days"]).isoformat()
            return close("executed", f"PO placed with {vendor['name']} for {a['qty']} x {a['sku']} {a['size']} "
                                     f"(${a['amount']:.2f}); expected arrival {arrival}")

        acct = _row(conn, "SELECT * FROM cash_accounts WHERE name = ?", (a["account"],), "Cash account missing")
        if acct["balance"] < a["amount"]:
            return refuse(f"{a['account']} balance ${acct['balance']:.2f} is less than ${a['amount']:.2f}; "
                          "paying would go negative")

        if a["kind"] == "invoice_payment":
            inv = _row(conn, "SELECT status FROM invoices WHERE id = ?", (a["ref_id"],), "Invoice missing")
            if inv["status"] != "open":
                return refuse(f"invoice {a['ref_id']} is already '{inv['status']}'")
            conn.execute("UPDATE invoices SET status = 'paid' WHERE id = ?", (a["ref_id"],))
            what, kind = f"invoice {a['ref_id']} marked paid", "invoice"
        else:
            lease = _row(conn, "SELECT next_due FROM leases WHERE id = ?", (a["ref_id"],), "Lease missing")
            new_due = _add_month(date.fromisoformat(lease["next_due"])).isoformat()
            conn.execute("UPDATE leases SET next_due = ? WHERE id = ?", (new_due, a["ref_id"]))
            what, kind = f"lease {a['ref_id']} next_due {lease['next_due']} -> {new_due}", "rent"

        new_balance = round(acct["balance"] - a["amount"], 2)
        conn.execute("UPDATE cash_accounts SET balance = ?, date = ? WHERE name = ?",
                     (new_balance, today.isoformat(), a["account"]))
        pay = conn.execute(
            "INSERT INTO payments (kind, ref_id, amount, account, paid_at, approved_by) VALUES (?, ?, ?, ?, ?, ?)",
            (kind, a["ref_id"], a["amount"], a["account"], today.isoformat(), approver))
        result = close("executed", f"Paid ${a['amount']:.2f} from {a['account']} (payment {pay.lastrowid}); "
                                   f"{what}; balance now ${new_balance:.2f}")
        return {**result, "payment_id": pay.lastrowid, "new_balance": new_balance}


# Agents never see the money-moving tool: it's only registered on a human-mode server.
if MCP_ROLE == "human":
    mcp.tool(human_decision_record)


if __name__ == "__main__":
    mcp.run(show_banner=False)
