# Agent Court: Dashboard Design

The Campus Customs ops desk (`frontend/`, React + Vite + TypeScript) shows the agent team as a pickup basketball game on an outdoor court. Tickets are basketballs. When you pick one, the ball goes to the Boss, gets passed along to exactly the specialists who work it, comes back as each finishes, and is then swished into the hoop by the specialist the ticket was assigned to. The finished ticket drops to the ground under **Resolved Tickets**. The whole board runs on the Problem 7 routes at `http://localhost:8000`.

## Layout

The page is a two-column grid: the game on the left, the controls and records on the right. On narrow screens it stacks into one column.

| Area | Where | What it shows |
|---|---|---|
| **Top bar** | Full width | Campus Customs title (pixel font, Yale blue and gold), an LED **scoreboard** for checking cash in the center, a Live/Offline light, and **Reset DB**. |
| **Unresolved Tickets** | Left, top | One basketball per open ticket, labelled with its ID, alongside a card with the ticket type, subject and requester. Click a ball to send it to the team. While a run is going, the other balls are disabled (one run at a time) and the ball in play is ghosted with a dashed outline. |
| **The court** | Left, middle | An outdoor court: pixel-style sky and clouds, a stylized campus skyline with a gothic tower, trees, a chain-link fence, a Yale-blue asphalt court with white lines and a "CAMPUS CUSTOMS" center logo, and a hoop with an animated net. The five players stand in their positions. |
| **Resolved Tickets** | Left, bottom (the grass) | Balls that have been scored land here with a bounce. Each shows the ticket subject, the Boss's 3–6 word headline, any human approval ("Jacob approved #1"), and a status chip. |
| **Human Approval Desk** | Right, top | Pending payment and purchase-order requests, with **Approve** / **Reject** buttons. |
| **Team recap** | Right, middle | A per-agent summary for the selected ticket, with a **Short / Technical** toggle and any drafts left on the board. |
| **Play-by-play** | Right, bottom | A live, newest-first feed of every event: tip-off, tool calls, results, passes, scores, approvals, resets. |

## How the agents read differently

Each agent is a fictional cartoon player, drawn in SVG and not based on any real person. The team differs in age, gender and race, and each player has a distinct jersey color and number, so you can tell who's who at a glance:

| Agent | Player | Look | Court spot |
|---|---|---|---|
| **Boss** | Coach Gloria #1 | Older Black woman with a gray natural afro, navy jersey with gold trim | Center: the ball always starts with her |
| **Inventory** | Kenji #23 | Young East Asian man, short fade with a pink headband, light-blue jersey | Up top, near the fence |
| **Accounting** | Priya #8 | South Asian woman with a bun and glasses, green jersey | Front left |
| **Facilities** | Walt #44 | Older white man, bald with a gray beard, orange jersey | Far left wing |
| **Customer Service** | Luz #11 | Young Latina woman with a high ponytail that sways, purple jersey | Front right |

**Player states:**
- **Idle:** slightly desaturated.
- **Working:** a gold glow, a dribbling bob, and a blinking gold light on the nameplate.
- **Done:** full color and a green light.
- **Shooting:** only the specialist the ticket was assigned to shoots. They jump and raise the shooting arm while the ball arcs to the hoop.

**Speech bubbles** show what each agent is doing right now. Each kind has its own style:
- 💭 thinking (blue, italic)
- 💬 talking (white)
- 🔧 calling an MCP tool (yellow, monospace, with arguments)
- ✅ a tool's answer (green, monospace)
- 🏀 a pass to a teammate, naming the need (orange)
- 🏁 the agent's finished summary (green)
- ⚠️ a refused tool call (red)

Bubbles fade 8 seconds after the final shot so the court resets for the next ticket.

**The ball tells the routing story.** There is one ball per ticket, and it only ever goes to agents who actually work that ticket, following the same chain the code enforces:
1. The ball drops from the ticket rack into the **Boss's** hands.
2. The Boss passes it to the **one routed specialist** for that ticket type.
3. If that specialist brings in a helper (for example Accounting for a payment request, or Customer Service for a draft), the ball is passed on to the helper.
4. When a helper finishes, they pass the ball back to whoever brought them in. When the routed specialist finishes, they pass it back to the Boss. If the Boss then brings in Customer Service for a draft, the ball goes there and back too.
5. When the run ends, the ball goes back to the **routed specialist, the lead the ticket was assigned to, who takes the only shot**: *swish*.

The net stretches and sways, "SWISH!" pops above the rim, and the ball bounces to the ground before reappearing under Resolved Tickets. Players who never touch the ticket stay idle. For example, on the rent ticket only Boss → Facilities → Accounting handle the ball, and Facilities sinks it.

## How resolved tickets show up

A ticket moves to **Resolved Tickets** as soon as its run finishes. The chip shows the honest database status:
- **Resolved ✓** (green): done.
- **Needs your approval** (gold): the team finished, but a payment or order is waiting on a human.
- **Blocked** (red): needs a follow-up.

When a human approves the last pending request on a ticket, the backend closes it on its own, and the chip flips to Resolved ✓. Clicking a landed ball opens its recap:
- **Short:** one or two plain sentences per agent (the Boss's headline and decision).
- **Technical:** each agent's technical summary, chips for every MCP tool it called (with counts), its handoffs and their needs, approval and draft IDs, and the status the Boss set.

Drafts appear in a collapsible "Drafts on the board (not sent)" list.

## How cash shows up

Cash lives on an arcade-style LED **scoreboard** in the top bar:
- **Main number:** the current **checking balance** in glowing yellow digits, read from `cash_accounts`.
- **Second line:** money already requested (Pending), what's **Left if approved**, and the shop date.

When a human approves a payment on the **Human Approval Desk**, cash moves in the backend and the balance drops right away. A red "−$2,400.00"-style tag pops out of the scoreboard and fades. A reset shows a green "+" tag.

**How the approval desk works:**
- Each request shows its kind (💵 invoice payment, 🏠 rent payment, 📦 purchase order), amount, ticket, who requested it, and the agent's reason.
- The Approve and Reject buttons stay disabled until you type your name. The name is recorded as `approved_by` and in the audit trail.
- If the backend refuses a payment (it would overdraw, or the vendor is still blocked), the refusal appears on the request and in a red toast.

## Why someone would like this

An ops dashboard is usually a wall of tables. This one turns the agent team into something you can watch and root for. Each ticket is a possession, and you can see who has the ball, who they pass to and why, what they're saying and which tools they're calling. The ball moves only between the players who actually touch the ticket, and when the work is done, the assigned lead sinks it with a satisfying swish. The game isn't just decoration: the passes are the real handoffs, the swish is the real finished ticket run, and the scoreboard is the real bank balance. So the fun parts double as an audit you can follow at a glance. The approval desk keeps the human in charge. Watching your balance drop only when *you* hit Approve makes it obvious that the agents prepare the play but never spend the money. That's reassuring, easy to explain to a non-technical shop owner, and more engaging than refreshing a log file.
