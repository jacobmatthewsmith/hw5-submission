# Campus Customs Multi-Agent Ops — Harness

This is the working reference for the Campus Customs agent team: a Boss and four specialists (PydanticAI, `gpt-6-luna` through Portkey) that work tickets off a shared board. All shop data goes through one MCP server, a FastAPI backend serves the routes, and a React dashboard lets a human watch the agents and approve money.

**Contents:**
- [Data files](#data-files)
- [Agents](#agents)
- [Tables](#tables) (all 9, every field)
- [Which agent uses which tables](#which-agent-uses-which-tables)
- [The three open tickets](#the-three-open-tickets-and-how-they-link)
- [MCP tools: the three ticket tools](#mcp-tools--the-three-ticket-tools-problem-3)
- [Agent team](#agent-team-problem-5) (the five agents, routing and handoffs)
- [MCP tool catalog](#mcp-tool-catalog-all-tools-kept-current) (all 11 tools and the tables each reads and writes)
- [Audit trail](#audit-trail--outputaudit_trailjson)
- [Safety guardrails](#safety-guardrails)
- [Backend routes](#backend-routes-problem-7)
- [Dashboard](#dashboard-problem-8)
- [Full run results](#full-run-problem-9)

## Data files

| File | Role |
|---|---|
| `data/campus_customs.db` | Original shop database, unzipped from `data.zip`. **Never modified.** Set to read-only on disk so it can be used to reset the working copy. |
| `data/campus_customs_new.db` | Working copy. The MCP server and backend read and write this file as tickets get resolved. Reset it by copying the original over it before any full run. |
| `output/audit_trail.json` | Append-only record of every agent run, ticket run, human decision, reset and replay. |
| `output/resolved_tickets.json`, `output/desk_tickets.html`, `output/resolved_board.html` | Results of the clean full run (see [Full run](#full-run-problem-9)). |

## Agents

| Agent | Job |
|---|---|
| **Boss** | Reads tickets, routes each one to the specialist its type calls for, makes the final call (including discounts), and sets the final status. |
| **Inventory** | Checks stock by SKU and size, spots shortfalls, finds a vendor to restock. |
| **Accounting** | Watches cash and invoices, checks margins, prepares payments and purchase orders for human approval. |
| **Facilities** | Handles the shop lease and rent. |
| **Customer Service** | Drafts messages to customers. Drafts stay on the board; nothing is sent. |

Prompts: `backend/prompts/<agent>.md` (four paragraphs each). The full table of each agent's tools and outputs is under [Agent team](#agent-team-problem-5).

Each ticket goes to the Boss, who routes it to one specialist; that specialist brings in others only as needed (see **Routing and handoffs** below).

---

## Tables

The database has 9 tables. Row counts and values below describe the **original** database, before any run. "Today" for the shop is `desk.date_today` = **2026-08-31**. The working copy also gets three board-state tables; see [Board-state tables](#board-state-tables-working-copy-only).

### `desk` — 1 row

| Field | Type | Meaning | Current value |
|---|---|---|---|
| `date_today` | TEXT | The shop's "today". Every overdue / due-soon check uses this, not the real clock. | `2026-08-31` |
| `notes` | TEXT | Free-text desk notes. | empty |

**Why it matters:** Every agent needs `date_today` to decide what is late. Accounting compares it to `invoices.due_date`, Facilities compares it to `leases.next_due`, and Inventory adds `vendors.lead_days` to it to get a restock arrival date.

### `tickets` — 3 rows (all `open`)

| Field | Type | Meaning |
|---|---|---|
| `id` | INTEGER PK | Ticket number (101–103). |
| `type` | TEXT | Kind of request: `customer_order`, `rent_notice`, `price_override`. |
| `requester` | TEXT | Who raised it (customer, landlord, student org). |
| `subject` | TEXT | Short title shown on the board. |
| `sku` | TEXT | Product involved, links to `inventory.sku` / `pricing.sku`. |
| `size` | TEXT | Size involved, links to `inventory.size`. |
| `qty` | INTEGER | Units requested. |
| `lease_id` | INTEGER FK → `leases.id` | Lease involved (rent tickets). |
| `invoice_id` | INTEGER FK → `invoices.id` | Vendor invoice involved. |
| `status` | TEXT | Ticket state. Only `open` exists so far. |
| `notes` | TEXT | Request details in the requester's words. |
| `created_at` | TEXT | ISO timestamp the ticket landed. |

**Why it matters:** This is the board. The Boss reads `type`, `subject`, and `notes` to route each ticket. The link fields (`sku`/`size`/`qty`, `lease_id`, `invoice_id`) tell the specialist exactly which rows to look up. Every agent updates `status` (and possibly `notes`) as work progresses.

### `inventory` — 10 rows (PK = `sku` + `size`)

| Field | Type | Meaning |
|---|---|---|
| `sku` | TEXT | Product code. |
| `name` | TEXT | Product name. |
| `size` | TEXT | S / M / L / XL, or `OS` (one size). |
| `qty` | INTEGER | Units on hand. |
| `location` | TEXT | Aisle where it's stocked. |

**Why it matters:** Inventory compares `qty` to the ticket's requested quantity to find shortfalls. Customer Service uses it to tell a customer what's actually available. Zero-stock rows right now: `CC-TEE-WHITE` S and `CC-MUG-CREST` OS.

### `pricing` — 4 rows

| Field | Type | Meaning |
|---|---|---|
| `sku` | TEXT PK | Product code. |
| `unit_cost` | REAL | What the shop pays per unit. |
| `list_price` | REAL | What the shop charges per unit. |

**Why it matters:** Accounting uses `list_price − unit_cost` to check margins before approving a discount, and `unit_cost × qty` to size a restock purchase order. The Boss uses the margin to make the final call on price overrides.

| SKU | Cost | List | Margin / unit | Margin % |
|---|---|---|---|---|
| CC-HOOD-NAVY | 22.00 | 58.00 | 36.00 | 62% |
| CC-TEE-WHITE | 8.00 | 28.00 | 20.00 | 71% |
| CC-HAT-BLUE | 6.00 | 22.00 | 16.00 | 73% |
| CC-MUG-CREST | 3.50 | 14.00 | 10.50 | 75% |

### `vendors` — 3 rows

| Field | Type | Meaning |
|---|---|---|
| `id` | INTEGER PK | Vendor id, referenced by `invoices.vendor_id`. |
| `name` | TEXT | Vendor name. |
| `specialty` | TEXT | What they supply. |
| `lead_days` | INTEGER | Days from order to delivery. |

| id | Vendor | Specialty | Lead days |
|---|---|---|---|
| 1 | Bulldog Print Co | apparel reprint | 5 |
| 2 | Elm City Gifts | mugs and small goods | 3 |
| 3 | QuickShip CT | local courier | 1 |

**Why it matters:** Inventory picks the restock vendor by `specialty` and estimates arrival as `date_today + lead_days`. **Rule:** a vendor will not ship while it has an open unpaid invoice, so Inventory has to check `invoices` for that vendor and hand off to Accounting if anything is open. Vendors are fictional: agents never contact them, they only draft.

### `leases` — 1 row

| Field | Type | Meaning |
|---|---|---|
| `id` | INTEGER PK | Lease id, referenced by `tickets.lease_id`. |
| `space_name` | TEXT | The rented space. |
| `landlord` | TEXT | Who is owed rent. |
| `monthly_rent` | REAL | Rent amount. |
| `next_due` | TEXT | Next rent due date. Should advance one month once rent is paid. |
| `notes` | TEXT | Free text. |

**Why it matters:** Facilities owns this table. It compares `next_due` with `date_today` to decide urgency and asks Accounting to prepare the rent payment for `monthly_rent`. Current lease: Chapel Street shop, Elm City Properties, **$2,400 due 2026-09-02**.

### `cash_accounts` — 1 row

| Field | Type | Meaning |
|---|---|---|
| `name` | TEXT PK | Account name (`checking`). |
| `balance` | REAL | Cash available. |
| `date` | TEXT | Date the balance was last updated. |

**Why it matters:** Accounting checks `balance` before preparing any payment. **Rule:** the pay tool must refuse if the balance would go negative. Cash only goes out in this homework; nothing ever adds to it. Current balance: **$3,400.00 in checking**.

### `payments` — 0 rows

| Field | Type | Meaning |
|---|---|---|
| `id` | INTEGER PK | Payment id. |
| `kind` | TEXT | What was paid, e.g. invoice or rent. |
| `ref_id` | INTEGER | Id of the thing paid (`invoices.id` or `leases.id`). |
| `amount` | REAL | Amount paid. |
| `account` | TEXT | Which `cash_accounts.name` it came from. |
| `paid_at` | TEXT | When it was paid. |
| `approved_by` | TEXT | The human who approved it. Required (`NOT NULL`). |

**Why it matters:** This is the audit record of money leaving the shop. A row is written only after a human approves the payment. Every payment also has to lower `cash_accounts.balance` and update the thing paid (`invoices.status` → paid, or `leases.next_due` → next month). Accounting writes it, and the Boss and the dashboard read it.

### `invoices` — 1 row

| Field | Type | Meaning |
|---|---|---|
| `id` | INTEGER PK | Invoice id, referenced by `tickets.invoice_id`. |
| `vendor_id` | INTEGER FK → `vendors.id` | Who billed us. |
| `amount` | REAL | Amount owed. |
| `due_date` | TEXT | When it's due. |
| `status` | TEXT | `open` (unpaid) or paid. |
| `description` | TEXT | What it's for. |

**Why it matters:** Accounting tracks what's owed and overdue. Inventory checks it because an open invoice blocks that vendor from shipping. Current invoice: **#501, Bulldog Print Co, $840, due 2026-08-28, open**, "Rush reprint CC-TEE-WHITE S". It is 3 days overdue as of `date_today`.

---

## Which agent uses which tables

| Table | Boss | Inventory | Accounting | Facilities | Customer Service |
|---|---|---|---|---|---|
| `desk` | ✓ | ✓ | ✓ | ✓ | |
| `tickets` | ✓ (routes, closes) | ✓ | ✓ | ✓ | ✓ |
| `inventory` | | ✓ (owner) | | | ✓ |
| `pricing` | ✓ | ✓ | ✓ (margins) | | ✓ (quotes) |
| `vendors` | | ✓ (owner) | ✓ | | |
| `leases` | | | ✓ | ✓ (owner) | |
| `cash_accounts` | ✓ | | ✓ (owner) | ✓ | |
| `payments` | ✓ | | ✓ (owner) | ✓ | |
| `invoices` | | ✓ (vendor block check) | ✓ (owner) | | |

---

## The three open tickets and how they link

**#101 — customer_order — Tauhid Zaman — Bulldog tee (CC-TEE-WHITE, S, qty 1)**
- `inventory`: CC-TEE-WHITE size S has **0** on hand. That's a shortfall of 1.
- `invoice_id` → **#501**: Bulldog Print Co (vendor 1), $840, "Rush reprint CC-TEE-WHITE S", due 2026-08-28, **open and overdue**.
- `vendors`: Bulldog Print Co is the apparel vendor (5-day lead). It won't ship the reprint while #501 is unpaid.
- Chain: Inventory finds the shortfall → Accounting prepares payment of #501 → **human approves** → vendor can ship, arriving about 5 days after payment → Customer Service drafts an update for Tauhid.

**#102 — rent_notice — Elm City Properties — Rent due (lease 1)**
- `lease_id` → **lease 1**: Chapel Street shop, $2,400, next due **2026-09-02** (2 days after `date_today`, not yet overdue).
- `cash_accounts`: checking has $3,400.
- Chain: Facilities confirms the amount and due date → Accounting prepares the rent payment → **human approves** → `payments` row, balance drops, `leases.next_due` moves to 2026-10-02.

**#103 — price_override — Yale AI Club — Bulk hoodie discount (CC-HOOD-NAVY, M, qty 20)**
- `inventory`: CC-HOOD-NAVY M has **8** on hand, a **shortfall of 12**. Other sizes: S 4, L 14, XL 6.
- `pricing`: cost $22, list $58, so $36 margin per unit. At list price, 20 hoodies = $1,160 revenue against $440 cost. Any discount should be checked against that margin.
- `vendors`: a restock of 12 would come from Bulldog Print Co (apparel), which is **also blocked by open invoice #501**.
- Chain: Inventory reports the shortfall and that the vendor is blocked → Accounting checks the margin on the requested discount (and the restock PO cost, 12 × $22 = $264) → Boss decides → Customer Service drafts the reply to the club.

### Cross-ticket observations

- **Cash is tight.** Invoice #501 ($840) + rent ($2,400) = $3,240 of the $3,400 balance, which would leave **$160**. A hoodie restock PO for 12 units ($264) would not fit after both payments. The agents will have to prioritize, and the pay tool must refuse anything that would go negative.
- **Invoice #501 unblocks two tickets.** Paying it is the prerequisite for restocking both the tee (#101) and the hoodies (#103).
- **Not referenced by any ticket:** CC-HAT-BLUE (40 on hand), CC-MUG-CREST (0 on hand), vendors 2 and 3.
- **Schema gaps to handle in later problems:** there is no table for purchase orders, pending approvals, or customer-message drafts. Those will need new tables or board state in the working copy (never in the original). *(Handled in Problem 5: see "Board-state tables" below.)*

---

## MCP tools — the three ticket tools (Problem 3)

Server: `mcp_server/server.py` (FastMCP), pointed at `data/campus_customs_new.db`. Every agent calls these tools rather than reading the database directly. Tools return only values from the database (plus arithmetic on them) and raise an error if a row is missing. They never fill in or invent data. Each tool's name uses its own words, with none shared between tools.

| Tool | Reads tables | Unlocks ticket | Why this is the right tool for that ticket |
|---|---|---|---|
| `vendor_invoice_blockers(invoice_id?, vendor_id?)` | `invoices`, `vendors`, `desk` | **101** | Ticket 101 points at invoice #501, which is open and 3 days overdue to Bulldog Print Co. Because a vendor won't ship while it has an unpaid invoice, this tool is what reveals that the size S tee can't be restocked until #501 is paid. It also gives the 5-day lead time, so the agents can tell the customer when the tee can actually arrive. |
| `lease_rent_schedule(lease_id)` | `leases`, `cash_accounts`, `desk` | **102** | Ticket 102 is a rent notice tied to lease 1, so Facilities needs the exact rent ($2,400), the due date (2026-09-02), and how many days remain relative to `desk.date_today`. The tool puts those next to the checking balance so the agents can confirm the payment won't push cash negative before asking a human to approve it. |
| `stock_margin_quote(sku, size, qty, discount_pct?)` | `inventory`, `pricing` | **103** | Ticket 103 asks for 20 size-M hoodies at a discount, which raises two questions: whether we have enough stock, and whether the discount still leaves a healthy margin. This tool answers both at once. It shows 8 on hand (a 12-unit shortfall and a $264 restock cost), and it computes the margin at list price and at any proposed discount, so the Boss can decide with real numbers. |

**Secondary uses:** `stock_margin_quote` also confirms ticket 101's shortfall (0 size-S tees on hand), and `vendor_invoice_blockers` also shows that ticket 103's hoodie restock is blocked by the same open invoice #501.

---

## Agent team (Problem 5)

Built with **PydanticAI**. Every agent uses the same model, **`gpt-6-luna` through Portkey** (`PORTKEY_API_KEY`, gateway `https://api.portkey.ai/v1`). `MODEL_NAME` in `backend/agents.py` is the only model string in the project.

| Agent | Prompt | Job | MCP tools it can call | Writes it can make | Returns |
|---|---|---|---|---|---|
| **Boss** | `backend/prompts/boss.md` | Opens the ticket, decides who works on it, makes the final call and sets the final status. Owns discount decisions. | `ticket_dossier_fetch`, `desk_board_overview`, `cash_position_report`, `status_note_update` | Ticket status and notes; the only role that can set `resolved` | `BossDecision` |
| **Inventory** | `backend/prompts/inventory.md` | Stock by SKU and size, shortfalls, picks a restock vendor and checks whether it's blocked. | `ticket_dossier_fetch`, `stock_margin_quote`, `supplier_catalog_search`, `vendor_invoice_blockers`, `status_note_update` | Ticket notes | `AgentReport` |
| **Accounting** | `backend/prompts/accounting.md` | Cash, invoices, margins. The only role that files payment and PO requests, and only for human approval. | `ticket_dossier_fetch`, `cash_position_report`, `approval_request_file`, `vendor_invoice_blockers`, `lease_rent_schedule`, `stock_margin_quote`, `status_note_update` | Approval requests (pending), ticket notes | `AgentReport` |
| **Facilities** | `backend/prompts/facilities.md` | Lease and rent: verifies rent notices, judges urgency, asks Accounting to queue rent. | `ticket_dossier_fetch`, `lease_rent_schedule`, `cash_position_report`, `message_draft_post`, `status_note_update` | Landlord drafts, ticket notes | `AgentReport` |
| **Customer Service** | `backend/prompts/customer_service.md` | Writes customer, landlord and vendor messages as drafts only. | `ticket_dossier_fetch`, `stock_margin_quote`, `message_draft_post`, `status_note_update` | Drafts, ticket notes | `AgentReport` |

### Routing and handoffs

The team is connected, so any specialist can bring in any other, but the code decides **who goes first, who can hand off, and why**. No ticket is ever sent to the whole team.

1. **Boss → one first specialist, chosen by ticket type.** The Boss's `route_ticket` tool has no "who" argument; the code looks up the ticket type (read through MCP) in `ROUTING`:

   | Ticket type | Routed to | Why |
   |---|---|---|
   | `customer_order` | Inventory | First question: can we fill it? |
   | `rent_notice` | Facilities | Owns the lease and can verify the notice |
   | `price_override` | Inventory | Check we can fill it before pricing it |
   | anything else | nobody | The Boss sets the ticket to `blocked` for a human to route |

2. **The routed specialist may bring in others, by need, not by name.** `ask_teammate(need, request)` maps each need to exactly one owner:

   | Need | Owner |
   |---|---|
   | `payment_or_po_request` | Accounting (the only role that files approvals) |
   | `margin_or_cash_review` | Accounting |
   | `stock_or_vendor_check` | Inventory |
   | `lease_or_rent_check` | Facilities |
   | `customer_draft` | Customer Service |

3. **Helpers can't hand off further.** A specialist brought in as a helper never sees `ask_teammate`, because the tool is hidden for that role.
4. **A specialist can be brought back at most once, and only for a different need** (`MAX_VISITS_PER_SPECIALIST = 2`). For example, Accounting can do a margin review and then a payment/PO request, but can't be asked for the same need twice. A return visit doesn't count as a new specialist.
5. **At most 3 specialists per ticket** (`MAX_SPECIALISTS_PER_TICKET`), so the whole team can never be on one ticket.
6. **The Boss gets one optional follow-up after routing** (`MAX_BOSS_FOLLOW_UPS = 1`), and only for a `customer_draft` (for example after a discount call) or a `payment_or_po_request` the routed specialist reported but didn't file. The Boss can't call Facilities or Inventory directly, and the follow-up still counts toward the once-each and 3-specialist limits.
7. Asking for your own need, routing twice, or the Boss asking before routing is refused with a message explaining why. Every route and handoff (from, to, need, request) is recorded in the ticket's `routing` record in the audit trail.

**Expected shapes for the three open tickets:**

| Ticket | Route | Likely handoffs | Max specialists |
|---|---|---|---|
| 101 customer_order | Boss → Inventory | Inventory → Accounting (`payment_or_po_request`, invoice #501), Inventory → Customer Service (`customer_draft` for Tauhid) | 3 |
| 102 rent_notice | Boss → Facilities | Facilities → Accounting (`payment_or_po_request`, rent). Facilities drafts any landlord note itself | 2 |
| 103 price_override | Boss → Inventory | Inventory → Accounting (`payment_or_po_request` + margins), then Boss → Customer Service (`customer_draft` once the discount is decided) | 3 |

**Agent loop** (`backend/agents.py: run_agent`, `backend/team.py: run_ticket`):
1. `team.py` starts a ticket run. It reads the ticket's type through MCP, launches one agent-mode MCP server (stdio) for the whole run, and starts the Boss on the ticket. The Boss routes it as described above.
2. Each agent runs PydanticAI's loop (`Agent.iter`): user prompt → model request → model response (reasoning, text, tool calls) → tool results → … → structured output.
3. Each step is recorded as it happens. When the agent run ends, the run is appended to `output/audit_trail.json` (see below), whether it succeeded, errored, or was stopped by a limit.
4. Tickets run one at a time (`--all` goes through them in id order), because they share one cash balance.

**Files:** `backend/models.py` (data types: `AgentReport`, `BossDecision`, `Finding`, `HandoffNeed`, `Handoff`, `TicketRouting`, `TeamDeps`, `AuditRecord`, `AuditStep`), `backend/agents.py` (model, agents, tool access, routing and handoffs, agent loop), `backend/team.py` (ticket runs, DB reset, CLI), `backend/audit.py` (append-only audit trail), `backend/prompts/*.md` (one prompt per agent).

```bash
.venv/bin/python backend/team.py --ticket 101        # one ticket
.venv/bin/python backend/team.py --reset --all       # restore working DB, then every open ticket
```

---

## MCP tool catalog (all tools, kept current)

Server: `mcp_server/server.py`, working DB `data/campus_customs_new.db`. No two tool names share a word. Shop facts reach the agents **only** through these tools; there is no other data layer.

| # | Tool | Added | Reads | Writes | Used by | What it's for |
|---|---|---|---|---|---|---|
| 1 | `desk_board_overview(status?)` | P5 | `desk`, `tickets` | — | Boss, `team.py` | The board: shop today plus tickets, optionally filtered by status. |
| 2 | `ticket_dossier_fetch(ticket_id)` | P5 | `tickets`, `desk`, `inventory`, `pricing`, `leases`, `invoices`, `vendors`, `approvals`, `drafts`, `ticket_log` | — | all agents | One ticket plus everything it links to and everything already done on it. |
| 3 | `status_note_update(ticket_id, agent, status, note)` | P5 | `tickets`, `approvals` | `tickets.status`, `ticket_log` | all agents | Moves a ticket along with a logged reason. Only the Boss can resolve, and never while an approval is pending. |
| 4 | `stock_margin_quote(sku, size, qty, discount_pct?)` | P3 | `inventory`, `pricing` | — | Inventory, Accounting, Customer Service | Stock by size, shortfall, restock cost, margin at list price and at a discount. **Unlocks 103.** |
| 5 | `supplier_catalog_search(specialty_keyword?)` | P5 | `vendors`, `invoices`, `desk` | — | Inventory | Vendors with lead time, open invoices, `can_ship`, and arrival if ordered today. |
| 6 | `vendor_invoice_blockers(invoice_id?, vendor_id?)` | P3 | `invoices`, `vendors`, `desk` | — | Inventory, Accounting | Is this vendor blocked by an open invoice? Days overdue, lead time. **Unlocks 101.** |
| 7 | `lease_rent_schedule(lease_id)` | P3 | `leases`, `cash_accounts`, `desk` | — | Facilities, Accounting | Rent, due date, days until due, whether cash covers it. **Unlocks 102.** |
| 8 | `cash_position_report()` | P5 | `cash_accounts`, `approvals`, `invoices`, `vendors`, `payments`, `desk` | — | Boss, Accounting, Facilities | Balance, pending payment total, available after pending, open invoices, past payments. |
| 9 | `approval_request_file(ticket_id, kind, requested_by, reason, …)` | P5 | `tickets`, `invoices`, `leases`, `vendors`, `inventory`, `pricing`, `cash_accounts` | `approvals` (status `pending`) | Accounting only | Queues an invoice payment, rent payment or purchase order **for a human**. The amount is computed from the DB. Duplicates are refused. |
| 10 | `message_draft_post(ticket_id, author, recipient, subject, body)` | P5 | `tickets` | `drafts` (status can only be `draft`) | Customer Service, Facilities | Saves a message on the board. There is no send tool. |
| 11 | `human_decision_record(approval_id, decision, approver, comment?)` | P5 | `approvals`, `cash_accounts`, `invoices`, `leases`, `vendors`, `desk` | `approvals`, `payments`, `cash_accounts`, `invoices`, `leases`, `ticket_log` | **Humans only** (dashboard / backend approval endpoint) | Approve or reject a pending request. Approving a payment pays it. It refuses if cash would go negative or the invoice is no longer open. Approving a PO places it, and it refuses while the vendor has an open invoice. |

Tool 11 is only registered when the server runs with `CAMPUS_MCP_ROLE=human`. The agents' server runs in agent mode, so the tool doesn't exist for them. It's also missing from every agent's allow-list and refuses to run in agent mode.

### Board-state tables (working copy only)

Created by the MCP server with `CREATE TABLE IF NOT EXISTS` inside `campus_customs_new.db`. They are never in the original, so a reset clears them.

| Table | Fields | Why |
|---|---|---|
| `approvals` | `id, ticket_id, kind (invoice_payment / rent_payment / purchase_order), ref_id, vendor_id, sku, size, qty, amount, account, reason, requested_by, status (pending / executed / rejected), decided_by, decided_at, result_note, created_at` | The human approval queue. No money moves until a human approves a row here. |
| `drafts` | `id, ticket_id, author, recipient, subject, body, status (CHECK = 'draft'), created_at` | Messages wait on the board. The schema itself makes "sent" impossible. |
| `ticket_log` | `id, ticket_id, agent, status, note, created_at` | Who changed a ticket's status and why. The original `tickets.notes` is never overwritten. |

**When a human decides the last pending request on a ticket** that the Boss parked in `waiting_on_approval`, the ticket closes itself: `resolved` if every request was carried out, `blocked` (for a follow-up run) if any was rejected. This is logged in `ticket_log` under the human's name.

**When a human approves a payment**, `human_decision_record` does all of the following in one transaction: checks the balance, inserts a `payments` row (`approved_by` = the human's name, `paid_at` = shop today), lowers `cash_accounts.balance` and sets its `date`, and marks `invoices.status = 'paid'` or moves `leases.next_due` forward one month. **Purchase orders don't move cash** in this model. They are bought on credit: approving one records the order and its expected arrival (`shop today + lead_days`), and the vendor would bill it later as a new invoice, which would then go through the normal payment approval. That future invoice isn't created here, because its amount terms and due date aren't in the database and inventing them would break the no-invented-data rule.

---

## Audit trail — `output/audit_trail.json`

- A JSON array that is **only ever appended to**. Each write takes a file lock, re-reads the array, adds one record, and atomically replaces the file. If the file isn't a valid array, the write is refused rather than overwritten. Resetting the DB never touches it.
- **One `agent_run` record per agent run**, handed-off runs included. Fields: `ticket_run_id`, `agent_run_id`, `parent_run_id` (who handed off), `ticket_id`, `agent`, `model`, `role` (lead / routed / helper), `depth`, `chain` (for example `boss → inventory → accounting`), `started_at`/`finished_at`, `status` (ok / error / stopped), `prompt`, `steps`, `output`, `error`, `usage`.
- **`steps` is the agent loop, step by step:** `user_prompt` → `model_request` (tool results and retry prompts going back to the model) → `model_response` (the model's reasoning summary, text, and every tool call with its arguments) → … → `end` (structured output).
- **One `human_decision` record per Approve/Reject click**, with who clicked, which request, and the full result (payment id and new balance, or the refusal). **One `db_reset` record per reset.** A `db_replay` record marks a restore of the working DB by re-applying earlier recorded writes through the MCP tools, with no model calls (used once, see [Full run](#full-run-problem-9)).
- **One `ticket_run` record per ticket run** with the final output, total tokens and requests, the limits that applied, and a `routing` block: ticket type, who it was routed to, which specialists joined, and every handoff with its need and request.

---

## Safety guardrails

These are the rules a real shop would run this team under. Each one says where it is enforced: in the **code or tool** itself (hard), or in the **prompt** (soft).

**Money and approvals**
1. **No money moves without a named human's approval.** Agents can only *request* payments and POs (`approval_request_file` → `pending`). The one tool that pays (`human_decision_record`) isn't registered on the agents' MCP server, isn't in any agent's allow-list, refuses to run in agent mode, and rejects an approver whose name is an agent's. *(code)*
2. **Cash can never go negative.** Payment is refused at approval time if the balance is smaller than the amount, and the request stays pending for the human to reconsider. *(code)*
3. **Amounts come from the database, never from an agent.** Invoice payments use `invoices.amount`, rent uses `leases.monthly_rent`, and POs use `qty × pricing.unit_cost`. The agent can't type in a dollar figure. *(code)*
4. **No double payments or duplicate orders.** A second request for something already pending is refused, and paying an invoice that's no longer `open` is refused. *(code)*
5. **Separation of duties.** Only Accounting can file payment or PO requests, and only the Boss can resolve a ticket. The calling agent's name is stamped onto every write by the backend, so one agent can't pose as another. *(code)*
6. **Don't order from a blocked vendor.** A PO can't be executed while that vendor has an open invoice. *(code)*

**Communication and data**

7. **Never send an email, text or any message to a customer, vendor or landlord.** There is no send tool, and the `drafts` table only allows `status = 'draft'`. A human reviews every draft. *(code + prompt)*
8. **Never invent shop facts.** Every number, date, name and price must come from an MCP tool result. Tools raise an error instead of guessing when a row is missing, and agents must say "unknown" rather than fill a gap. *(code + prompt)*
9. **Agents only touch the working copy, through MCP.** `campus_customs.db` is read-only on disk and never opened by the server. Agents have no SQL or file access, only the tools on their allow-list (least privilege). *(code)*
10. **"Today" is `desk.date_today`.** Overdue, due-soon and arrival dates are computed from it, never from the real clock. *(code + prompt)*
11. **Nothing closes with money still in limbo.** A ticket can't be `resolved` while it has a pending approval. It stays `waiting_on_approval` for the human. *(code)*
12. **Everything is auditable.** Every agent run, step, tool call and reasoning summary is appended to `audit_trail.json`, which is never wiped. *(code)*

**Token budget**

13. **One model, kept lean.** Every agent uses `gpt-6-luna` with low reasoning effort and a 2,000-token cap per response. No other model appears in the code. *(code)*
14. **Hard per-ticket ceiling.** Every agent run in a ticket shares one usage counter: at most 40 model requests, 60 tool calls and 300,000 tokens per ticket. The run stops if it hits any of them. *(code)*
15. **Deliberate, bounded routing.** Each ticket goes to one specialist chosen by its type. Handoffs name a need and the code picks the agent. A specialist is brought back at most once and only for a new need, helpers can't hand off, and there are never more than 3 specialists on a ticket, so the whole team is never pulled in. *(code)*
16. **Bounded agent loops.** A single agent run is stopped after 8 model requests. *(code)*
17. **Don't re-fetch what you have.** Prompts tell agents to read each record once, keep notes short, and only bring in the teammates a ticket needs. Tool outputs are compact JSON, and the system prompt is not copied into every audit step. *(prompt + code)*

---

## Backend routes (Problem 7)

`backend/main.py` (FastAPI). Start it from `backend/` with `uvicorn main:app --reload --port 8000`, which serves the API at `http://localhost:8000`. CORS is open to the Vite dev server (`localhost:5173`). Shop data is read through the campus-customs MCP server, just as the agents read it.

- **`GET /tickets`**: returns every ticket with its status (open, in_progress, waiting_on_approval, blocked, resolved), the shop's today, and which ticket run, if any, is in progress.
- **`GET /tickets/{ticket_id}`**: returns one ticket with its linked inventory/pricing/lease/invoice rows plus its approval requests, drafts and agent notes, so the board can show drafts.
- **`POST /tickets/{ticket_id}/run`**: starts the agent team on that ticket in the background and returns a unique `ticket_run_id` immediately. It returns 404 for an unknown ticket and 409 if a run is already going, because tickets share cash.
- **`GET /events?since={id}&ticket_id={id}`**: returns agent events newer than `since` (run started, agent started, thinking, said, tool call, tool result, handoff, agent finished, run finished, approval decided, reset), so the board can poll and refresh during a run.
- **`GET /approvals`**: returns the payment and purchase-order requests the agents have queued that are waiting for a human.
- **`POST /approvals/{approval_id}/approve`** (body `{"approver": "<human name>"}`): the human approve button. For a payment, this is where cash actually moves; it returns 409 if cash would go negative or the vendor is still blocked.
- **`POST /approvals/{approval_id}/reject`** (body `{"approver": "<human name>", "comment": "..."}`): the human reject button, which closes the request with no money moved.
- **`GET /cash`**: returns the checking balance from `cash_accounts`, plus pending requests, what would be left if they're approved, and payments made.
- **`POST /reset`**: copies `data/campus_customs.db` over `data/campus_customs_new.db` for a fresh run. The original and the audit trail are untouched, and it's refused while a run is in progress.

**Why only humans can approve:** the approve and reject routes are the only code that calls `human_decision_record`, on a separate human-mode MCP server. Agents have no HTTP tool and run on an agent-mode server where that tool doesn't exist, and the tool rejects an approver whose name is an agent's. The interactive API docs are at `http://localhost:8000/docs`.

---

## Dashboard (Problem 8)

`frontend/` (React + Vite + TypeScript). Start it with `npm run dev` from `frontend/`; Vite serves it at `http://localhost:5173` and opens your browser. It calls the backend at `http://localhost:8000` (override with `VITE_API_URL`), whose CORS allows that origin. It polls `/events` every second and `/tickets`, `/cash` and `/approvals` every 5 seconds (and right after any run, approval or reset). The look and layout are described in `output/design.md`. The ticket ball follows the real handoff chain: Boss → routed specialist → helpers, back up the chain as each finishes. At the end of the run, the routed specialist (the lead the ticket was assigned to) takes the only shot.

| Board feature | Route(s) it uses |
|---|---|
| Unresolved / Resolved ticket balls | `GET /tickets` |
| Click a ball → the team plays it | `POST /tickets/{id}/run` |
| Players' speech bubbles, passes, the final swish, play-by-play | `GET /events?since=` |
| Team recap (Short / Technical) and drafts | `GET /events`, `GET /tickets/{id}` |
| Human Approval Desk | `GET /approvals`, `POST /approvals/{id}/approve`, `POST /approvals/{id}/reject` |
| Cash scoreboard | `GET /cash` |
| Reset DB button | `POST /reset` |

---

## Full run (Problem 9)

All three tickets were played one at a time on the dashboard after a reset (audit record 21), with a human approving requests on the approval desk. The ticket runs are audit records 28, 32, 39.

| Ticket | Route and handoffs | Human approvals | Final status | Checking |
|---|---|---|---|---|
| 101 Bulldog tee | Boss → Inventory → Accounting (payment / PO); Inventory → Customer Service (draft #1) | #1 invoice #501 $840.00 paid; #2 PO 1 × tee $8.00 (credit) | `waiting_on_approval`, stale: both approvals were clicked mid-run | $3,400.00 → $2,560.00 |
| 102 Rent due | Boss → Facilities → Accounting (payment / PO) | #3 rent $2,400.00 paid | `resolved` | $2,560.00 → $160.00 |
| 103 Bulk hoodie discount | Boss → Inventory → Accounting (margin review); Boss → Accounting again (PO) | #4 PO 12 × hoodie $264.00 (credit) | `resolved`; price $36.67/unit (40% margin floor) approved by the Boss | $160.00 → $160.00 |

**Cash:** $3,400.00 start − $840.00 − $2,400.00 = **$160.00**, which matches `cash_accounts.checking` ($160.00), so the difference is $0.00. The itemized ledger is on the Cash tab of `output/desk_tickets.html`.

**Where to find the results:**
- **`output/desk_tickets.html`:** Expected vs Actual per ticket, the Cash tab, and the Reflection tab.
- **`output/resolved_tickets.json`:** per ticket, the outcome, what each agent contributed, the MCP tools it used, and the human approvals.
- **`output/resolved_board.html`:** screenshots of the React board per resolved ticket.

**Issues the run surfaced:**
1. **Stale final status (101).** A human approved both requests while the run was still going, but the Boss set `waiting_on_approval` from the earlier handoff report. Nothing was pending. A fix would be for `status_note_update` to refuse `waiting_on_approval` when no approval is pending (or settle the ticket immediately), and for the Boss to re-read `ticket_dossier_fetch` before setting the final status.
2. **No customer draft on 103.** The Boss used its one follow-up on the purchase order, so no draft reached the Yale AI Club.
3. **"Resolved" means the approvals are done, not that goods arrived.** There are no shipment or receiving tools yet.
4. **The working DB was reset after the run.** It was restored by replaying the run's 16 recorded writes from the audit trail through the MCP tools (record 41, 0 mismatches, no model calls), so `cash_accounts` reflects the run again.
