# Campus Customs: Multi-Agent Ops Desk (AI Foundations HW 5)

A five-agent team runs the back office of **Campus Customs**, a fictional Yale merch shop. Tickets (a customer order, a rent notice, a bulk-discount request) land on a board. A **Boss** agent routes each ticket to the right specialist (**Inventory**, **Accounting**, **Facilities**, **Customer Service**), and the specialists investigate through an MCP server and prepare any payment or purchase order. **A human approves every payment and purchase order in a React dashboard.** Agents can only request them.

It has three parts that talk to each other:

| Part | Folder | What it is |
|---|---|---|
| MCP server | `mcp_server/` | FastMCP server: the only way agents read or change shop data. 11 tools over `data/campus_customs_new.db`. |
| Backend | `backend/` | FastAPI app plus the PydanticAI agent team (all agents use **`gpt-6-luna` via Portkey**). Writes every agent step to `output/audit_trail.json`. |
| Dashboard | `frontend/` | React + Vite + TypeScript "Agent Court": tickets are basketballs, agents are players, and there's a human approval desk and a cash scoreboard. |

The full design reference (tables, tools, agents, routing rules, routes, safety guardrails, run results) is in **[`output/harness.md`](output/harness.md)**.

---

## 1. Prerequisites

- **Python 3.11+** (developed on 3.14)
- **Node.js 20.19+** and npm (developed on Node 24)
- A **Portkey API key** that can reach `gpt-6-luna`

Commands below are for macOS/Linux and are run from the repository root unless a step says `cd`. On Windows, use `.venv\Scripts\python` / `.venv\Scripts\activate` in place of `.venv/bin/python` / `source .venv/bin/activate`, and `copy` in place of `cp`.

## 2. Install

```bash
git clone https://github.com/jacobmatthewsmith/hw5-submission.git
cd hw5-submission

# Python dependencies (FastMCP, PydanticAI, FastAPI, uvicorn) in a project venv
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Frontend dependencies (exact versions from package-lock.json)
cd frontend
npm ci
cd ..
```

Keep the venv at `.venv/` in the repo root: `.mcp.json` points at `.venv/bin/python`.

## 3. Configure environment variables

```bash
cp .env.example .env
```

Open `.env` and set `PORTKEY_API_KEY` to your Portkey key. That's the only required variable; `.env.example` explains the optional ones. `.env` is git-ignored. The backend also finds a `.env` up to two folders above the repo, if you'd rather keep the key outside the clone.

## 4. Databases: original vs. working copy

| File | Role |
|---|---|
| `data/campus_customs.db` | The original shop database. **Never modified**; it's the reset source. |
| `data/campus_customs_new.db` | The working copy. The MCP server, backend and agents read and write **only** this file. |

**As submitted, the working copy holds the end state of the graded three-ticket run** (checking $160.00, invoice #501 paid, rent paid, two purchase orders placed). That's what the dashboard and the reports in `output/` show. To start a clean run, copy the original over the working copy:

```bash
cp data/campus_customs.db data/campus_customs_new.db
```

**Resetting replaces the working database with the original.** All tickets go back to `open`, checking goes back to $3,400.00, and the board tables (approvals, drafts, ticket notes) are emptied. The audit trail (`output/audit_trail.json`) is never touched by a reset. The dashboard's **⟲ Reset DB** button and `POST /reset` do the same copy, and are refused while a ticket run is in progress.

## 5. Start the MCP server

You don't have to start it by hand to use the app. **The backend launches its own MCP server processes** over stdio: an agent-mode one for the agents, and a human-mode one only when someone clicks Approve/Reject. To run or inspect it on its own:

```bash
source .venv/bin/activate

# list the tools (agent mode: 10 tools; the human-only payment tool is hidden)
fastmcp list mcp_server/server.py

# call a read-only tool against the working DB
fastmcp call mcp_server/server.py lease_rent_schedule lease_id=1

# run it as a stdio server (it waits for an MCP client on stdin; Ctrl+C to stop)
python mcp_server/server.py
```

`.mcp.json` registers the same server for an MCP client such as Claude Code (open the client in the repo root). See [`mcp_server/README.md`](mcp_server/README.md) for the tool list.

## 6. Start the FastAPI backend

In a terminal (venv active, `.env` configured):

```bash
cd backend
uvicorn main:app --reload --port 8000
```

The API is at **http://localhost:8000**, with interactive docs at http://localhost:8000/docs. CORS allows the Vite dev server at `http://localhost:5173`.

| Route | What it does |
|---|---|
| `GET /tickets` | All tickets with their status, plus any run in progress |
| `GET /tickets/{id}` | One ticket with its linked data, approval requests, drafts and agent notes |
| `POST /tickets/{id}/run` | Starts the agent team on that ticket in the background (one run at a time) |
| `GET /events?since={id}` | Live agent events: thinking, speech, tool calls and results, handoffs |
| `GET /approvals` | Payment and purchase-order requests waiting for a human |
| `POST /approvals/{id}/approve` | **Human only.** Body `{"approver": "<your name>"}`. A payment moves cash here |
| `POST /approvals/{id}/reject` | **Human only.** Body `{"approver": "<your name>", "comment": "..."}` |
| `GET /cash` | Checking balance from `cash_accounts`, plus pending requests and payments |
| `POST /reset` | Copies the original DB over the working DB (refused during a run) |

## 7. Start the React frontend

In a second terminal:

```bash
cd frontend
npm run dev
```

Vite serves the board at **http://localhost:5173** and opens it in your browser. It calls the backend at `http://localhost:8000`; set `VITE_API_URL` in `frontend/.env.local` to change that. `npm run build` type-checks and builds a production bundle.

## 8. Use the app

1. Open **http://localhost:5173**. The LED scoreboard shows the checking balance.
2. In the **Human Approval Desk** (top right; below the court on narrow windows), type your name. Approve and Reject stay disabled until you do, and your name is recorded as the approver.
3. Click a ticket ball under **Unresolved Tickets**. The ball goes to the Boss, gets passed along the real handoff chain, and the assigned specialist swishes it. Speech bubbles show each agent's reasoning, tool calls and results. A run takes about 1–2 minutes.
4. When requests appear on the desk, click **Approve & pay** / **Approve order** or **Reject**. Approving a payment drops the scoreboard balance right away. The backend refuses a payment that would make cash negative, and a purchase order from a vendor that still has an unpaid invoice.
5. Click a ball under **Resolved Tickets** to see the **Team recap** (Short / Technical toggle) and any drafts. Drafts are never sent.

## 9. Full three-ticket run (clean)

1. Stop any run in progress, then reset the working DB (this replaces it with the original):
   ```bash
   cp data/campus_customs.db data/campus_customs_new.db
   ```
   Or click **⟲ Reset DB** on the board. Checking should read **$3,400.00** and all three tickets should be `open`.
2. With the backend and frontend running, play **101**, then **102**, then **103**, one at a time, approving or rejecting what lands on the desk.
3. Optional, headless: `python backend/team.py --reset --all` resets the DB and runs all three tickets from the terminal. Approvals still go through the dashboard or the approve route.

Every run is appended to `output/audit_trail.json`, which is never wiped.

---

## What's in `output/`

| File | Contents |
|---|---|
| `harness.md` | The design reference: tables, MCP tools, the five agents, routing rules, routes, dashboard, safety guardrails, run results |
| `mcp_smoke.json` | Smoke test of the first three MCP tools from the vibe coder, cross-checked against the DB |
| `desk_tickets.html` | Per ticket: Expected (my plan) vs Actual (the run), a Cash tab reconciling to `cash_accounts`, and a Reflection tab. Open by double-clicking |
| `design.md` | How the dashboard looks and why |
| `resolved_tickets.json` | Per ticket: final status, outcome, what each agent contributed, tools used, human approvals |
| `resolved_board.html` | Screenshots of the React board for each resolved ticket. Open by double-clicking |
| `audit_trail.json` | Append-only record of every agent run (each loop step, tool call and reasoning summary), ticket run, human decision, reset and replay |
| `github_url.txt` | This repository's URL |

**Results of the graded run:**

| Ticket | Final status | Cash |
|---|---|---|
| 101 | `waiting_on_approval`. This is a known agent mistake: both approvals were executed mid-run and the Boss reported a stale status | Invoice #501 paid, $3,400 → $2,560 |
| 102 | `resolved` | Rent paid, → $160 |
| 103 | `resolved` | $264 hoodie PO placed on credit. No customer draft was written |

Ending checking is **$160.00**, matching `cash_accounts` (difference $0.00). Details and the reasoning are in `output/desk_tickets.html` and `output/harness.md`.

## Safety, in short

- Agents can only *request* payments and purchase orders. The tool that pays only exists on a human-mode MCP server and needs a human approver's name.
- Cash can never go negative, amounts always come from the database, and duplicate requests are refused.
- There is no send tool. Messages are saved as drafts and never sent.
- Only `gpt-6-luna` is used, with per-ticket caps on tokens, requests, tool calls and handoffs.

The full list of 17 guardrails is in `output/harness.md`.

## Repository layout

```
AI_prompts.md          every prompt I sent the AI coding assistant, by problem
requirements.txt       Python dependencies
.env.example           environment template (copy to .env)
.mcp.json              MCP server registration for an MCP client
data/                  campus_customs.db (original), campus_customs_new.db (working)
mcp_server/            server.py, README.md
backend/               main.py (FastAPI), models.py, agents.py, team.py, audit.py, events.py, prompts/*.md
frontend/              React + Vite + TypeScript dashboard
output/                harness, smoke test, reports, audit trail, repo URL
```
