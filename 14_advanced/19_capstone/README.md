# Module 19 – Capstone Part 1: Architecture, Build & Integration

**Capstone application: Warranty & Returns Resolution Assistant** for an electronics retailer ("ElectroMart").

A customer writes in ("my headphones stopped charging after 5 months, I want a refund").
The system finds the order, reads the warranty/returns policy that applies, decides
refund / replacement / repair / reject with a policy citation, drafts the reply, and sends
high-value refunds and every rejection to a human approver.

- Slides: `Module_19_Capstone_Part_1.pptx` (28 slides; the last two are the demo guide below)
- Everything is synthetic. Run all commands from this folder (`14_advanced/19_capstone`) with the repo's `.venv` active.

## Files

| File | What it is | Needs |
|---|---|---|
| `capstone_common.py` | Paths, business limits, the "demo clock" | – |
| `19_1_generate_sample_data.py` | 7 policy PDFs (37 clauses), `orders.db` (15 orders), 20 test tickets | – |
| `19_2_ingest_policies.py` | RAG layer: clause-level chunks → Chroma; hybrid retrieval (embeddings + BM25, RRF) with metadata filter | step 1 |
| `19_3_mcp_orders_server.py` | MCP server: `get_order`, `get_customer_orders`, `get_past_claims` (read-only) | step 1 |
| `19_4_mcp_notify_server.py` | MCP server: `send_approval_request` (log + optional ntfy push) | – |
| `19_5_guardrails.py` | Input rails, PII scrubbing (Presidio), output validators | – |
| `19_6_agent_graph.py` | LangGraph agent loop: triage → research ∥ investigate → decide → write ⇄ review → validate → approval gate | steps 1–2 |
| `19_7_api.py` | FastAPI backend: tickets, SSE stream, approvals, `/metrics` | steps 1–2 |
| `19_8_ui_streamlit.py` | Streamlit UI: customer chat + approver panel | `19_7` running |
| `19_9_run_test_tickets.py` | Runs the 20 test tickets, prints a scorecard | steps 1–2 |
| `monitoring/` | Prometheus (host port 9096) + Grafana (host port 3001), dashboard pre-provisioned | Docker, `19_7` running |

Every numbered file runs on its own and prints its own demo.

## Two modes

- **LLM mode** (default when `OPENAI_API_KEY` is set): Triage, Resolution Writer and Reviewer use `gpt-4o-mini`.
- **Offline mode** (`--offline`, or no key): those three steps use keyword/template stand-ins.
  Retrieval, MCP tool calls, decision rules, guardrails and the approval gate are the same code in both modes.
  If an LLM call fails in LLM mode, the ticket falls back to the stand-ins for 60 seconds instead of failing.

The **decision** itself is never made by the LLM: it is rules applied to the retrieved clauses and the
order facts, so money decisions are repeatable. The LLM does the language work.

## Demo guide – what to run and what to show

### One-time setup
```
python 19_1_generate_sample_data.py
python 19_2_ingest_policies.py
```
Re-run both to reset the demo (close any policy PDF you have open first – an open PDF is locked).

### Each layer on its own

| # | Run | What to show | Time |
|---|---|---|---|
| 1 | `python 19_1_generate_sample_data.py` | The raw material. Open `data/policies/Warranty_Policy.pdf`: numbered clauses. Open `data/test_tickets.json`: each ticket has an expected decision. | instant |
| 2 | `python 19_2_ingest_policies.py` | "One chunk, as stored" – one clause with its metadata. Then the same headphones question **without** and **with** the category filter: without it the appliance and accessory warranty clauses leak in; with it clause 4.2 is returned. Note "found by semantic / keyword". Try your own: `python 19_2_ingest_policies.py "is water damage covered"` | ~10 s |
| 3 | `python 19_3_mcp_orders_server.py --test` | The client **discovers** three tools. A normal lookup, the repeat claimant's two past claims, an unknown order, and `1; DROP TABLE orders` rejected by server-side validation. | ~5 s |
| 4 | `python 19_4_mcp_notify_server.py --test` | The only action the agent may take alone: ask a human. Show the new line in `data/approval_requests.log`. (If `NTFY_TOPIC` is set in `.env` this also pushes to your phone; set `CAPSTONE_NO_PUSH=1` to stop that.) | ~5 s |
| 5 | `python 19_5_guardrails.py` | Input rails: injection blocked, poem blocked, phone/e-mail/card masked. Output validators: one reply passes, three fail (refund above order value, invented clause, leaked e-mail + false promise). | ~25 s (Presidio loads a language model) |

### The whole system

| # | Run | What to show |
|---|---|---|
| 6a | `python 19_6_agent_graph.py` | One ticket, node by node. The customer asks for a **refund**; the system decides **replacement** and cites Warranty Policy clauses 4.2 and 8.2. Point out the two parallel agents (policy + order). |
| 6b | `python 19_6_agent_graph.py --ticket T03` | A Rs. 65,000 refund: the graph **pauses** at the approval gate. Type `y` or `n` and watch it resume. (`--approve` / `--reject` answer for you.) |
| 6c | `python 19_6_agent_graph.py --ticket T07` | Liquid damage → reject → also needs a human (every rejection does). |
| 6d | `python 19_6_agent_graph.py --ticket T17` | Prompt injection: stopped at the input rail; no agent runs. |
| 6e | `python 19_6_agent_graph.py "My kettle from ORD-1011 does not heat"` | Any free-text ticket. |
| 7 | `python 19_7_api.py --test` | Every endpoint exercised in-process: create, poll, approvals, approve, the SSE stream, and the `/metrics` lines. |
| 8 | Terminal 1: `python 19_7_api.py`  Terminal 2: `streamlit run 19_8_ui_streamlit.py` | Customer tab: pick sample ticket T01, Submit, watch the agents work. Pick T03: it stops for approval → Approver tab → Approve → Customer tab → Check status. Then open `http://localhost:8019/docs` and `http://localhost:8019/metrics`. |
| 9 | `python 19_9_run_test_tickets.py` | The scorecard: expected vs got, who went to a human, citations, time per ticket. This is the iteration loop – change a prompt or a policy and re-run. |
| 10 | `cd monitoring` then `docker compose up -d` (with `19_7` running) | Grafana at `http://localhost:3001` (admin/admin): tickets by decision, latency per agent, token cost per ticket, errors, guardrail blocks, escalation rate. Submit a few tickets from the UI and watch it move. |
| 11 | LangSmith (`LANGSMITH_TRACING=true` in `.env`) | One trace per ticket named `ticket-TKT-…`; each agent is a span; open the Policy Researcher and Order Investigator spans. |

Add `--offline` to steps 6, 7 and 9 to run without the LLM.

Good tickets to show: **T01** (refund asked, replacement given), **T03** (approval), **T07/T08** (damage excluded),
**T13** (no order id), **T15** (repeat claimant → human), **T17** (injection), **T18** (PII masked).

## What has and has not been verified

Verified by running (offline mode):
- Steps 1–5 each run standalone and print the output described above.
- `19_6`: straight-through, approval (approve and reject), injection, missing order id, sales question.
- `19_7 --test`: all endpoints, including pause/resume and the SSE stream.
- `19_8`: driven headlessly against a live `19_7` – submit, progress, approval, final reply.
- `19_9 --offline`: **20 of 20** tickets correct, about 1 second per ticket.

Not verified – check these on your machine before the session:
- **LLM mode.** The environment this was built in cannot reach the OpenAI API, so the `gpt-4o-mini`
  prompts (triage, writer, reviewer) have not been run. Run `python 19_9_run_test_tickets.py` (no `--offline`)
  first; if a ticket fails it will most likely be a triage classification, fixed by tuning the `Triage` field
  descriptions in `19_6_agent_graph.py`.
- **Grafana / Prometheus.** Docker was not running, so the containers were not started. The config files parse,
  mirror the working Module 17 stack, and every metric name in the dashboard is served by `/metrics`.
- **LangSmith traces** were not inspected.
- The Streamlit UI was tested through Streamlit's test harness, not looked at in a browser.

## Design decisions

- **Refund limit:** refunds above Rs. 5,000 need a human; so does every rejection and any claim on an order with two earlier claims.
- **Repair threshold:** in-warranty defects after 30 days are replaced up to Rs. 10,000 and repaired above that.
- **Read-only tools:** the agent cannot write to the orders database; its only action is to send an approval request.
- **Every decision cites a policy clause** that was actually retrieved (enforced by an output validator).
- **PII is scrubbed before the graph starts**, so it reaches neither the LLM, the checkpoints, nor the traces.
- **Demo clock:** "today" is fixed at the day the data was generated (`data/meta.json`), so tickets do not drift out of their return window.
- **Two MCP servers, not three:** an earlier design had a Filesystem MCP server for policy documents; the policies are PDFs read through the RAG index, so it had no real job and was left out.
- **Ports:** API 8019, Prometheus 9096, Grafana 3001 – chosen not to collide with the Module 17 stack (9095/3000) or Langfuse (9090).
