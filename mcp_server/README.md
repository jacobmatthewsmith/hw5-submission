# Campus Customs MCP Server

`server.py` is a [FastMCP](https://gofastmcp.com) server that gives the Campus Customs agent team (Boss, Inventory, Accounting, Facilities, Customer Service) shared tools for the shop database. It is the **only** way agents see or change shop data. Tools return database values and simple arithmetic on them, and raise an error when a row is missing, so they never make up data.

## Database

- **Uses:** `data/campus_customs_new.db`, the working copy. The path is resolved relative to this folder.
- **Never touches:** `data/campus_customs.db`, the original. It stays static so the working copy can be reset with:

```bash
cp data/campus_customs.db data/campus_customs_new.db
```

On first use the server adds three board-state tables to the working copy: `approvals`, `drafts` and `ticket_log`. A reset removes them.

## Tools

| Tool | Reads | Writes | What it does |
|---|---|---|---|
| `desk_board_overview(status?)` | `desk`, `tickets` | — | Shop "today" plus the ticket board. |
| `ticket_dossier_fetch(ticket_id)` | `tickets`, `desk`, `inventory`, `pricing`, `leases`, `invoices`, `vendors`, `approvals`, `drafts`, `ticket_log` | — | One ticket with everything it links to and all work done on it so far. |
| `status_note_update(ticket_id, agent, status, note)` | `tickets`, `approvals` | `tickets`, `ticket_log` | Set status with a logged note. Only `boss` can resolve, and not while an approval is pending. |
| `stock_margin_quote(sku, size, qty, discount_pct?)` | `inventory`, `pricing` | — | Stock by size, shortfall, restock cost, margin at list price and at a discount. |
| `supplier_catalog_search(specialty_keyword?)` | `vendors`, `invoices`, `desk` | — | Vendors with lead time, open invoices, `can_ship`, and arrival if ordered today. |
| `vendor_invoice_blockers(invoice_id?, vendor_id?)` | `invoices`, `vendors`, `desk` | — | A vendor's open invoices, days overdue, and whether it can ship. |
| `lease_rent_schedule(lease_id)` | `leases`, `cash_accounts`, `desk` | — | Rent, due date, days until due, and whether cash covers it. |
| `cash_position_report()` | `cash_accounts`, `approvals`, `invoices`, `vendors`, `payments`, `desk` | — | Balance, pending payment total, available after pending, open invoices, payments. |
| `approval_request_file(...)` | `tickets`, `invoices`, `leases`, `vendors`, `inventory`, `pricing`, `cash_accounts` | `approvals` | Queue a payment or PO for human approval. Accounting only; the amount comes from the DB. |
| `message_draft_post(...)` | `tickets` | `drafts` | Save a message as a draft. Nothing is ever sent. |
| `human_decision_record(...)` | `approvals`, `cash_accounts`, `invoices`, `leases`, `vendors`, `desk` | `approvals`, `payments`, `cash_accounts`, `invoices`, `leases`, `ticket_log` | **Human mode only.** Approve or reject a request. Approving a payment pays it, and it refuses if cash would go negative. Once nothing is pending on a `waiting_on_approval` ticket, it sets the ticket to `resolved` (or `blocked` if anything was rejected). |

## Roles

- **Agent mode** (default, or `CAMPUS_MCP_ROLE=agent`): the first ten tools. The backend agents and the vibe coder (`.mcp.json`) use this mode, so neither can approve or pay anything.
- **Human mode** (`CAMPUS_MCP_ROLE=human`): also registers `human_decision_record`, for the dashboard's approval endpoint.

## Running

```bash
pip install -r requirements.txt
python mcp_server/server.py   # stdio transport, agent mode
```
