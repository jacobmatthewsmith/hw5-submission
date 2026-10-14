# AI Prompts Log — Campus Customs Multi-Agent Ops (HW 5)

This file lists every prompt I sent to the AI coding assistant, organized by problem, so a grader can see exactly what I asked it to do. Each problem is described in my own words.

How each section is organized:

- **Problem number and title.**
- **Prompt:** the first prompt I typed for that problem, copied word for word (typos included).
- **Follow-up:** any later prompts for the same problem, also copied word for word. Each one is followed by a bracketed sentence explaining what was missing from the earlier prompt or why the follow-up was needed.

---

## Problem 1: Vibe Coder Prompts

**Prompt:**

> Problem 1 - Vibe coder prompts
>
> Please set up AI_prompts.md and please record all the prompts i sned you here, cleanly organized. this should be a comprehensive guide that my grader will use to see what I prompted you to do. Each problem will be described in my own words Each section in this file should include - the problem number and title, at least one prompt that i typed, and follow up prompts if needed (please make sure to write in a sentence on what was missing in the first one)

---

## Problem 2: Study the Campus Customs Database

**Prompt:**

> Problem 2 - Study the Campus Customs database
>
> Unzip the data file i just added to the folder. Open data/campus_customs.db and analyze/review ever tables and all the fields. make a copy of this table (we're going to use both the copy and the original version in this assingment). later problems will update the working copy, while leaving the original untouched. We need to study the three open tickets so we can see how they link to other tables. Can you drop the three open tickets here so I can review them?
>
> We also need to start the output/harness.md folder - for each table, wer'e going to list the fiels and why this table matters for the agents. I assume this is table for each agent, explaining why they need the fields in the database/why they are relevant for those agents.
>
> We're going to keep adding to this harness file .

---

## Problem 3: Build the MCP Server

**Prompt:**

> Ok problem 3 - we need to make an MCP server in mcp_server/ this will use FASTMCP. i it should interact with data/campus_customes_new.db. You do not need to connect or run it just yet - we will get to that later. Every agent in this homework should also use the toold in this MCP server. We're going to add more tools later. we need to write 3 tools we know we will need for each of the above tickets - those tools we should build first and put here. The names of the toold should be very clear - try to keep the words in each tool name unique. NEVER invent any data whatsover, and only use information in the original database.
>
> In output/harness.md list each of our MCP tools. For each tool pleas einclude in this harness file - which table it reads, which ticket it helps unlock (101, 102, or 103). Please also write a sentence on why this is the right tool for that ticket.
>
> Please make sure the explanation for these tool <> ticket ties are at least 10 words - it is ideally a full sentence and a fully explained thought.
>
> Also add a short mcp_server/README.md file that explains what the MCP server is for, which database file it uses, and the three tools it has

---

## Problem 4: Connect the MCP Server to the Vibe Coder and Smoke-Test Each Tool

**Prompt:**

> Problem 4 - Add the MCP server to the vibe coder and test each tool
>
> In our vibe coder (here in claude) we're going to add the MCP server to the project. This is so that the vibe coder can call the tools. Save the connection JSON text in a new .mcp.json at the project root (double check this - should be copascetic with with how claude has been saving local mcp server lists
>
> Once vibe coder is connected, test each of the three mcp tools. Save the evidence in a new file - output/mcp_smoke.json
>
> For each tool please include
>
> The prompt we built for the vibe coder
> The name of the tool you developed (the unique one)
> The tool output (must match values in data/campus_customs_new.db

---

## Problem 5: Build the Agent Team and Grow the MCP Tools

**Prompt:**

> Problem 5 - Build the agent team and grow the MCP tools
>
> We need to next build the agentic team for campus customs. This will be agents who work togethers. These should use pydanticAI - Boss, Inventory, Accounting, Facilities, and Customer service. 5 agents total.
>
> Please build prompts, models, and agent loops so that it is easya nd efficient for them to work together in full connectivity.
>
> Put these agent prompts into backend/prompts/ folder - there should be one file per agent. Data types should go in backend/models.py and the files for the agents should be under backend/ (The five roles must be clear, the structure is flexible). PLease make sure to use portkey_api_key and gpt-6-luna for each agent>
>
> Please write extremely detailed prompts for this agent with shop rules. These should cover all aspects of the agents work (see above for eahc of their scopes)
>
> it's very important that these prompts are detailed enoguh - i would say at least 2 paragraphs, but feel free to write up to 4 paragraph prompts.
>
> Add the tools we need for the agents to the MCP server so that they can open and work on tickets. Shop facts should only come from the MCP server over data/campus_customs_new.db - never ever invite a second shop tools layer with invente dinfo that bypasses the MCP.
>
> Wire agents so that they append information to the output/audit_trail.json as they run - we want a detailed record of their work and thinking. for each agent-run be sure to include agent loop step, with a record enough for an audit later. Append to this file each time. Never wipe it after a run.
>
> in output/harness.md - we need to list out each agent and each MCP tool (include every tool that was added from thisproblem as wella s future ones). Please also include which table the tool is using. Also include a saftey section in the harness. Please write at least 10 bullets in the safety section with rules like never send an email, never spend money without human approavl. these should be safety gaurdrails that a real bsuiness would use. Please also make at least 3 rules that keep tokens in check. 10ish rules total.
>
> Please update mcp_server/README.md so the tool list matches what we have now.

---

## Problem 6: Plan the Three Tickets

**Prompt:**

> problem 6 - Plan the three tickets
>
> Before we fully build out the backend - can you write down what you expect the team to do on each open ticket? Build output/desk_tickets.html - this should be a page when you can double click with one tab per ticket (101, 102, 103). There should also be an empty cash and reflection tabs for later problems we work on (just leave these blank with a coming later note for now)
>
> For each ticket tab, complete an expected section - leave room for an actual section we'll fill post-agent run
>
> For each tickets expected section - I need to write in my own words. please use basically the text below since it's part of the assignment:
>
> 101/102/103
> Who the boss should call first and why
> All the agent delegations I expect
> Which MCP tools I expect the run to use
>
>
> Can you list out the MCP tools, remind me what the ticket numbers and contents are and the agent names so I can work on this? Then I will keep giving you problem 6 - feel free to work on the other parts of problem 6, and I will come back to you with the "in my own words" section (i just need these details reposted here first.

**Follow-up:**

> OK here it is in my own words - please clean this up just a bit (typos etc)
>
> Ticket 101 — Bulldog tee
>
> Who the Boss shoud call first and why:
> I woud have the Boss call Inventory frist becuase the size S tee is out of stock. We need to knwo if we can restock it and whats holdign that up.
>
> Delegations I expcet:
> Boss asks Inventory to check stock and supliers. Inventory finds the unpaid invoice #501 is blocking Bulldog Print Co, then asks Accoutning to check the invocie and cash. Accounting takes the upcomign rent into account and reqeusts human approval for payment, checking that ticket 103 hasnt already reqeusted the same payment. Accounting reports back to Inventory about payment, and Inventory asks Customer Service to drfat an udpate for Tauhid. We shoudnt promise the tee right away becuase the supplier has a five-day lead time once the block is cleared. Boss reveiws whats still pending and sets the status.
>
> MCP tools:
> Boss: desk_board_overview, ticket_dossier_fetch. Inventory: stock_margin_quote, supplier_catalog_search, vendor_invoice_blockers. Accounting: cash_position_report, vendor_invoice_blockers, approval_request_file. Customer Service: message_draft_post. Handoffs and udpates use ask_teammate and status_note_update.
>
> Ticket 102 — Rent due
>
> Who the Boss shoud call first and why:
> Facilities frist becuase they handle the lease and can confrim the rent amount and due date.
>
> Delegations I expcet:
> Boss asks Facilities to check the notice agaisnt the lease. Facilities confrims $2,400 is due September 2, two days away, then asks Accounting to queue payment. Accounting checks availble cash and exisitng reqeusts, then files for human approval. It shoud flag to Boss that paying rent plus invoice #501 leaves just $160. Accounting reports back to Facilities and Boss. Facilities can drfat a landlord mesage if needed. Boss sets the status based on whehter payment is still pending or acutally paid.
>
> MCP tools:
> Boss: desk_board_overview, ticket_dossier_fetch. Facilities: lease_rent_schedule, and message_draft_post if a mesage is needed. Accounting: cash_position_report, approval_request_file. Handoffs and udpates use ask_teammate and status_note_update.
>
> Ticket 103 — Bulk hoodie discount
>
> Who the Boss shoud call first and why:
> Inventory frist becuase we need to knwo if we can fill the order before commiting to a disocunt.
>
> Delegations I expcet:
> Boss asks Inventory to check the 20 medium hoodies. Inventory finds only eight availble, so we need 12 more, and asks Accounting to check restock costs and disocunt margins. Accounting finds the $264 restock is blocked by the same invocie #501 and coordiantes with ticket 101 to avoid duplicate payment reqeusts. It also flags that rent plus the invocie leaves $160, so were $104 short for restocking. Accounting gives Boss the cash situation and possble margins. Boss makes the final disocunt decision and decides how to proceed. Accounting files any needed payment or purchase order reqeusts for human approval. Boss then asks Customer Service to drfat the proposed price and availablity mesage and sets the ticket status.
>
> MCP tools:
> Boss: desk_board_overview, ticket_dossier_fetch. Inventory: stock_margin_quote, supplier_catalog_search, vendor_invoice_blockers. Accounting: stock_margin_quote, cash_position_report, vendor_invoice_blockers, approval_request_file. Customer Service: message_draft_post. Handoffs and udpates use ask_teammate and status_note_update.
>
> For all three, mesages stay as drafts and only a human uses human_decision_record to approve or reject reqeusts. The agents cant approve their own payments.

[Needed because the first prompt only set up the page and asked for a reference sheet of tickets, agents and tools; this follow-up supplies my own expected plan for each ticket to fill in the Expected sections.]

**Follow-up:**

> OK 2 is fine plase make that note
>
>
> for number 1 that's fine - confirming that is because we would wait for a hypotehtically invoice - ie were buying it on credit?

[Needed because the assistant pointed out two places where my expectations differed from the build: the Boss may skip `desk_board_overview`, and purchase orders don't take cash. I asked for a note on the first and confirmed the reasoning behind the second.]

**Follow-up:**

> Ok and noting - we should really avoid putting every specialist on every ticket - i will get a very low score. it's important that only identified agents for ticket types get tagged in (bosses job) - every ticket should go to boss > 1 agent. NO MORE.

[Needed because the build let any agent delegate to any other (up to 6 hand-offs per ticket), and my expected plans had chains like Inventory to Accounting to Customer Service. This sets the rule that the Boss routes each ticket to only the agent identified for its ticket type.]

**Follow-up:**

> wait do you feel like the second one (Order→Inv, Rent→Fac, Price→Inv) is copascetic with instructions?

[Needed because after I picked a strict one-agent routing, I wanted to check it against the assignment's role scopes. The assistant pointed out that strict routing conflicts with full connectivity and with Accounting owning payment requests.]

**Follow-up:**

> I think it's fine to call on more than once agent - we just need code that is very deliberate on how this is done. Calling on all 5 agents or sending to all 5 would be bad. It needs to be structured so that it goes to one first, and then they can call on others as needed.

[Needed to settle the routing rule: the Boss sends each ticket to one specialist first, and that specialist may bring in others only as needed, under deliberate code-enforced limits.]

---

## Problem 7: Backend Routes

**Prompt:**

> OK problem 7 - Backend routes
>
> We need to make a backend for our React frontend dashboard (this is coming in the next problem). In backend backslash main.py, we need to do the following in order for our fast API and routes to work. So using fast API and add the routes.
>
> return the three tickets and the status. So include whether they are open or resolved.
>
> take a ticket ID. So grab the ticket ID and run your agent team on that ticket ID. So these ticket IDs should be unique.
>
> Return recent or just happened agent events - what each agent said, did, and what tools they used to get the job done - this is so that the board can refresh
>
> Approve a payment (again only a human should approve payments) Or a purchase (diito) after a human clicks the approve button you will build. (Agina - agents only porpepare the payment/tee it up, the approval button is where a cash transaction would take place.
>
> We need a route to returnt he current checking balance from cash_accounts
>
>
> Reset the the database to the original values (again this is why we duplicated) when we want to try a fresh run.
>
> From the backend/ folder, we'll start the server with
>
> uvicorn main:app --reload --port 8000
>
> This will activate our backend at http://localhost:8000 so that the fornt end dahs board can call these routes.
>
> in output/harness.md, list each route in one sentence (the URL and what it does)

---

## Problem 8: Frontend Agent Dashboard

**Prompt:**

> Problem 8 - ok next, we need to build our front end agent dashboard in frontend/ with a react + vite + typescript stack. The page should call the routes we built in the last problem and at minimum the board should
>
> list all three tickets
>
> let me pick a ticket for the agent team to work on.
>
> show each agent and what they are saying, doing while they are working.
>
> Mark a ticket resolved when the run finishes
>
> show a short summary of what each agent did on the ticket (ideally there would be a short summary that is one two sentences summarizing a second more technical summary that mentions the tools it used and other steps it took - please let me toggle between these)
>
> Make a button/workflow for a human to approve of a payment or a purchse when approrpriate.
>
> Show the checking account balance (it should drop after an approved pay)
>
> I would like the agents to be displayed as basketball players (diverse ages, genders, races) - they should not be real people, but either cartoons or some other rendering. I'd like them to shoot a ball into a hoop and the ball should swish once they are done with their work. They should be standing outside on a basketball court. (fine to do this in retro arcade game style, or anything else)
>
> A ticket should be a basketball at the top of the screen with a clear description of what the ticket is and it's ID. (and they should be in a clear section called "Unresolved Tickets) when I choose a ticket, i will click on it and the ball will go to a player who will shoot it and score like the above. The ball should then fall to the ground with a few word summary fo the ticket title and a the balls should fall under a header "Resolved Tickets"
>
> Front end needs tot alk to backend at http://localhost:8000. On th ebackend - the Vite page origin (this is usally http://localhost:5173) so that the browser has permission to call on these routes.
>
> Start the board with
>
> npm run dev
>
> This opens react desk in my browser so you can pick tickets and watch agents
>
> Write output/design.md with a summary of how we designed the dashboard look - include the layout, how agents read differently, how resolved tickets and cash show up
>
> Please also write a short paragrah about why a user would like this (gamified, fun to see the agents score, etc)


**Follow-up** (sent with my Problem 9 prompt; logged here because it changes the Problem 8 dashboard):

> One more wuick design thing - the ticket/basketball should get passed between agents that are working on it (so if it starts with the boss agent, it goes to them first, THEN passed to another agent, then passed to any othe rhelper agents, before getting swished in the basket by the lead agent assigned. (please make sure all of the updates from this are recorded appropriately - might make sense to split this part of my message off into prompt 8 section fo the prompts folder - please make sure that everything in prompt 8 around descriptions etc happens to this)

[Needed because in the first version every specialist took its own shot when it finished. I wanted one ticket ball passed along the real handoff chain (Boss, then the routed specialist, then any helpers) and swished once by the specialist the ticket was assigned to.]
---

## Problem 9: Resolve the Tickets

**Prompt:**

> OK next Problem 9 : resolve the tickets
>
> I want to test the agents on a full run of the three tickets. please reset the working database to be data/campus_customs_new.db again so we can start clean. I'm going to be paying close attention to the starting checking balance
>
> I'm then going to run each ticket one at a time.
>
> Use output/desk_tickets.html from problem 6. On each ticket tab, fill the actual section from this run- pleas einclude which agents worked, what they delegated, and the tools that they used. Keep the expected section in tact so that we can compare. (i.e. do not edit the expected section)
>
> On the cash tab of output/desk_tickets.html, itemize the money with thetransactions that we completed. Show the starting checking balance (after the reset, before we start handling tickets)
>
> For each ticket, show how cash changes with that resolved ticket, and the reason why (whihc pay or purchases, the dollar amount)
>
> And the ending checking balance at the bottom - this must match cash_acocunts in the working database. Do not change the number in cash_accounts. Simply show the number from that one, and the delta between the two (this should be zero, but we will trouble shoot afterward)
>
> wrong cash math loses points, so I'll come back with feedback if it's off. you'll need to investigate.
>
> please also save:
>
> output/resolved_tickets.json - for each ticket: id, final status, short descriptions of outcome, what each agent contributed, and any human approvals.
>
> output/resolved_board.html - this is a page that can be double-clicked to see a screenshot of the react board for each resolved ticket (101, 102, 103)
>
> Make sure to append the real ticket runs to the output/audit_trail.json - make sure ot update the output/harness.md so that it includes the tables, mcp tools, the five agents and a descriotion of each, API routes, the dashboard and our safety rules.
>
> [One design paragraph from this message, about passing the ticket ball between agents, is logged as a follow-up under Problem 8.]
>
> Can you give me the browser link so i can resolve tickets? do i need to open terminal or are you able to handle that piece?

**Follow-up:**

> It froze when the ball went to the coach on the first ticket - can you fix this

[Needed because during the first real run the Boss's first model call through Portkey hung for about 90 seconds, so the board looked frozen with the ball in the coach's hands. That run also showed Inventory recommending an invoice payment without handing off to Accounting, which the fix addressed too.]

**Follow-up:**

> ok i ran all the tickets!

[Needed to tell the assistant the runs were done so it could check the results in the database and the audit trail before writing up the Actual sections, the Cash tab, and the other outputs.]

---

## Problem 10: Reflection

**Prompt:**

> ok I did a run and i have answers to the problem 10 questions:
>
> 1. How I would evaluate the agents on each ticket
>
> For ticket 101, I think the agents did the actual investigation well, but didnt finish the status update correctly. Boss sent it to Inventory, which confrimed there were zero small tees and found that invoice #501 was blocking Bulldog Print Co. Inventory brought in Accounting to request the $840 invoice payment and an $8 purchase order for one tee, then Customer Service to drfat a response to Tauhid. That was a sensible division of work, and the draft didnt promise a delivery date we couldnt guarantee.
> The main issue was that I approved both requests while the agents were still running. The invoice was paid and the PO was placed with an expected arrival of September 5, but Boss still marked the ticket waiting_on_approval and said the vendor was blocked. It was using old information from the handoff. The shirt still hadnt arrived, so fulfillment wasnt complete, but the reason given for waiting was no longer accurate.
> Ticket 102 was the cleanest. Boss called Facilities, Facilities checked the lease, and Accounting requested the $2,400 rent payment. They correctly identified September 2 as the due date, rather than treating rent as overdue. After I approved it, checking dropped from $2,560 to $160, the next rent date moved to October 2, and the ticket became resolved. They didnt bring in Inventory or Customer Service unnecessarily.
> Ticket 103 was mostly good on the numbers and purchasing, but weaker on communication. Inventory found eight medium hoodies and a shortfall of 12. Accounting calculated a price of about $36.67 to preserve the 40% margin floor, and Boss approved that price conditionally on restocking. Boss then brought Accounting back for a seperate need: requesting the $264 PO. I approved it, and the database marked the ticket resolved. However, no customer draft was created. Also, resolved here means the approval process was completed; it doesnt mean the hoodies arrived or the customer recieved them.
>
> 2. How Actual compared with Expected
>
> For 101, the delegation chain was pretty close to what I expected: Boss to Inventory, then Inventory to Accounting and Customer Service. The agents also requested an explicit one-unit PO, which my plan hadnt spelled out. The biggest difference was the stale final status after my approvals. I expected Boss to report what was actually still pending.
> For 102, the run followed my plan almost exactly. Facilities verified the lease and asked Accounting to queue payment. No landlord draft was created, but I had only expected one if needed. The cash calculation also matched: $3,400 minus the $840 invoice and $2,400 rent left $160.
> For 103, I expected Inventory, Accounting, and Customer Service. In the latest run, only Inventory and Accounting joined Boss, so the customer communication step was missing. The vendor also wasnt blocked anymore becuase I had already paid invoice #501 during ticket 101. That showed why the agents needed to check current information instead of assuming the original blocker still applied.
> I also need to correct my original cash assumption. I expected the $264 hoodie restock to create an immediate $104 shortfall against the remaining $160. In this app, POs are placed on credit and dont reduce checking. Accounting did flag the potential $104 gap if a later payment were required, but approving the PO itself left cash at $160. The $8 tee PO worked the same way.
> One smaller difference across all three was that Boss opened the supplied ticket directly with ticket_dossier_fetch instead of using desk_board_overview first.
>
> 3. What would have been simpler as one agent with tools
>
> The rent ticket would have been much simpler with one agent. It could check lease_rent_schedule, read cash_position_report, and file the payment request without passing the same facts through Boss, Facilities, and Accounting. The latest rent run used 14 model requests for a fairly straightforward task.
> One agent could probably handle much of 101 and 103 too, since stock, vendor blockers, cash, and margins already come from structured tools. Multiple agents made the responsibilities easier to follow, but added handoffs and opportunities for information to get stale, which happened on 101. A single agent would still need to refresh the state after human actions. Human approval should remain seperate either way.
>
> 4. Three new problems this team could handle with the existing tools
>
> First, another student group could request 30 Yale caps at a discount. The database has 40 caps, with a $6 cost and $22 list price. Inventory could check availability, Accounting could evaluate discounted margins with stock_margin_quote, Boss could decide the price, and Customer Service could draft the offer. Actually recording the sale would be outside the current tools.
> Second, a customer could request Crest Mugs, which currently have zero stock. Inventory could find Elm City Gifts through supplier_catalog_search and check its three-day lead time and invoice blockers. Accounting could request a PO for human approval, and Customer Service could draft an availability update, similar to the tee ticket.
> Third, the shop could recieve another rent notice for the Chapel Street lease. Facilities could compare it with lease_rent_schedule, and Accounting could check cash and existing requests before requesting payment. After the latest run, that would mean recognising the next due date is October 2 and that checking currently has only $160.
>
> 5. Three new problems it couldnt handle without additional tools
>
> First, Tauhid could return the tee and request a refund. Customer Service could draft a reply, but the app cant look up a completed sale, confirm the original payment, issue a refund, or put returned stock back into inventory. I would need sales lookup, return, refund-approval, and inventory-adjustment tools, used by Customer Service, Accounting, and Inventory.
> Second, Bulldog Print Co could say the 12 hoodies shipped, but only ten arrive. The current app records a PO and expected arrival, but cant track a shipment or record what physically arrived. Inventory would need shipment-tracking and goods-receipt tools, probably with a fulfillment agent to manage discrepancies. This is also why marking 103 resolved doesnt prove the order was fulfilled.
> Third, Campus Customs could need extra staff for a busy Yale event. None of the current tools contain employee availability, skills, hours, or payroll information. I would need a staffing agent with scheduling and availability tools, plus Accounting access to wage estimates and payroll approvals. The current inventory and cash tools could provide some context, but they couldnt build or execute a staffing plan.

---

## Problem 11: Prepare and Publish the Submission

**Prompt:**

> Please complete Problem 11 for my AI Foundations HW 5 project: prepare the project for submission and push it to a public GitHub repository that graders can clone and run.
> Work from the existing hw5 folder and preserve the current project, working database, and audit history.
>
> 1. Check the required files
>
> The repository should include:
> Project files:
>
> * AI_prompts.md
> * requirements.txt
> * .env.example
> * .gitignore
> * .mcp.json
> * README.md
>
> Both databases:
>
> * data/campus_customs.db
> * data/campus_customs_new.db
>
> MCP server:
>
> * mcp_server/server.py
> * mcp_server/README.md
>
> Frontend and backend:
>
> * frontend/ with its source files, package.json, lockfile, and configuration
> * backend/main.py
> * backend/models.py
> * All other backend files needed to run the app
> * backend/prompts/boss.md
> * backend/prompts/inventory.md
> * backend/prompts/accounting.md
> * backend/prompts/facilities.md
> * backend/prompts/customer_service.md
>
> Outputs:
>
> * output/harness.md
> * output/mcp_smoke.json
> * output/desk_tickets.html
> * output/design.md
> * output/resolved_tickets.json
> * output/resolved_board.html
> * output/audit_trail.json
> * output/github_url.txt
>
> Check which files already exist. If a required output is missing, generate it from the actual saved run results and database. Keep the reports consistent with the evidence, including any unresolved tickets or agent mistakes. Do not invent successful results or replace the existing audit trail.
>
> 2. Prepare the repository
>
> Never commit or push my real .env file or API keys. Make sure .env.example contains placeholders and explains the required variables. Check that .mcp.json is portable and contains no secrets.
> Set up .gitignore to exclude .env, .venv/, node_modules/, Python caches, and other unnecessary local files. Both database files and the required output files must remain included.
>
> 3. Write clear setup instructions
>
> Create or update the root README.md so a grader starting from a fresh clone can follow the exact commands to:
>
> * Install the Python and frontend dependencies.
> * Configure environment variables from .env.example.
> * Copy the original database to the working database when a clean run is needed.
> * Start the MCP server.
> * Start the FastAPI backend.
> * Start the React frontend.
> * Open the app and use the human approval controls.
> * Reset the working database before a full three-ticket run.
>
> Explain that resetting replaces the working database with the original. Preserve my current working database while preparing the submission.
>
> 4. Verify and publish
>
> Run the relevant existing checks and frontend build, and fix any submission-blocking issues. Check that the documented commands match the actual implementation.
> Use a repository dedicated to this homework. If one is already configured, use it; otherwise create a public GitHub repository using the available GitHub authentication. Commit and push the submission without force-pushing.
> Write the actual public repository URL into output/github_url.txt and commit and push that file too. Confirm that the repository is public and that both database files and all required deliverables are tracked.
> If GitHub authentication is unavailable, finish all local preparation and tell me the specific step needed to authenticate.
> When finished, give me the repository URL to paste into Canvas, briefly summarize verification, and flag any remaining submission requirements. I will submit the URL to Canvas myself.

---
