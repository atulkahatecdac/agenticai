# IT Helpdesk Copilot - BrightPath Solutions

An agentic IT helpdesk that runs **entirely locally**: employees describe a problem in plain
English and a team of agents troubleshoots it, unlocks accounts, handles access requests
(with a **human manager approving**), and escalates security incidents.

| Concept | Where |
|---|---|
| **RAG** over runbooks and policies, with citations | `1_ingest_kb.py`, `2_rag_kb_assistant.py` |
| **MCP servers** exposing live helpdesk data and actions | `3_mcp_helpdesk_server.py`, `4_mcp_identity_server.py` |
| **Tool-calling agent** (ReAct) mixing RAG and MCP tools | `5_tool_agent.py` |
| **Guardrails** (LLM classifiers on input and output) | `6_guardrails.py` |
| **Multi-agent graph**: triage router + specialists, **human-in-the-loop** approval | `7_helpdesk_graph.py` |
| **UI** (employee view + manager approval queue) | `8_app_flask.py` |
| **Evaluation** with LLM-as-judge | `9_run_test_requests.py` |

**Slides:** [`IT_Helpdesk_Capstone.pptx`](IT_Helpdesk_Capstone.pptx): 37 slides with speaker notes (architecture, one or more slides per step, code walkthrough per file, exercises).

**Stack:** Ollama (`qwen3:8b` chat, `nomic-embed-text` embeddings) · LangChain · LangGraph ·
langchain-mcp-adapters + FastMCP · Chroma · SQLite · Flask. No API keys.

## The data (written by hand, no generator scripts)

```
data/
  kb/                   8 Markdown documents - the knowledge base for RAG
    KB-101 VPN · KB-102 passwords & MFA · KB-103 email · KB-104 Wi-Fi & printing
    POL-201 access policy · POL-202 laptops · POL-203 security incidents · SLA-301 priorities
  seed.sql              employees, assets, entitlements, service status, tickets, access requests
  helpdesk.db           built from seed.sql (not committed: *.db is gitignored)
  test_requests.json    11 test requests with expected route + expected behaviour
```

The data is set up so that the right answer needs **both** RAG and live tools:

- **VPN is "degraded"** (Pune gateway maintenance), so the right answer is "switch to Mumbai", not a ticket.
- **Jira is "down"** for everyone, so the assistant should say so and not raise a duplicate ticket.
- **E1002 Rahul** has a **locked** account and a laptop bought in **2021**, which makes it eligible for a refresh under POL-202.
- **E1004 Karan** is a **contractor**. POL-201 forbids contractors from getting AWS Production.
- **Tableau** is a *restricted* system, so a request needs the manager's approval (human in the loop).

## Setup

```bash
ollama pull qwen3:8b
ollama pull nomic-embed-text
# from the repo root venv (requirements.txt already has everything)
cd 14_advanced/19_capstone/it_helpdesk
```

`*.db` files are gitignored, so build `data/helpdesk.db` once from `seed.sql`:

```bash
sqlite3 data\helpdesk.db < data\seed.sql
```

To **reset the demo** later (scripts create tickets, unlock accounts ...):

```bash
del data\helpdesk.db data\checkpoints.db data\notifications.log data\pending_threads.json
sqlite3 data\helpdesk.db < data\seed.sql
```

## Run the steps in order

```bash
python 1_ingest_kb.py                 # chunk + embed the KB into Chroma (once)
python 2_rag_kb_assistant.py          # grounded answers with [KB-xxx] citations; "I don't know" when not covered
python 3_mcp_helpdesk_server.py --test
python 4_mcp_identity_server.py --test
python 5_tool_agent.py                # one agent, 11 tools - watch the tool calls
python 6_guardrails.py                # injection / credential / off-topic blocking
python 7_helpdesk_graph.py            # the full multi-agent flow; approve the Tableau request in the terminal
python 8_app_flask.py                 # http://localhost:5021
python 9_run_test_requests.py         # routing accuracy + judge scores
```

## The graph (step 7)

```
guard_input ─┬─ blocked ──────────────────────────────────────────────► END
             └─ triage ─┬─ how_to ──────────── RAG chain ──────────┐
                        ├─ troubleshooting ─── ReAct agent ────────┤
                        ├─ access_request ──── ReAct agent ─┬──────┼─► guard_output ─► END
                        │                                   └─ manager_approval (interrupt)
                        └─ security_incident ─ fixed P1 ticket + alert, LLM writes reply
```

Things to point out:

1. **Each specialist gets only the tools it needs.** The troubleshooter can unlock accounts but can't request access. No LLM ever gets `decide_access_request`; only a human decision can call it.
2. **Defence in depth.** The access agent *reads* POL-201 (RAG) to explain the rules, and the Identity MCP server also *enforces* them in code. A manipulated LLM still can't get a contractor into AWS Production.
3. **Not everything should be agentic.** Security incidents always create a P1 ticket and alert IT Security in plain code. The LLM only writes the message.
4. **Human in the loop.** `interrupt()` saves the paused graph to `data/checkpoints.db`. The manager can approve later, even after a restart, and the graph resumes in `manager_approval`.
5. **Single agent vs. multi-agent.** Compare `5_tool_agent.py` with step 7 on the laptop-refresh request. The single agent tends to skip the policy lookup and pick the wrong priority.

## Exercises

- Highly restricted systems need **manager + IT Security**. Add a second `interrupt()` for the Security approval.
- Add a **conversation memory** so the employee can answer the access agent's "what is the business reason?" question.
- Switch to `HELPDESK_MODEL=llama3.2` and re-run step 9. Which routes break first?
- Add an MCP tool `get_ticket_status(ticket_id)` and test that the agent uses it for "what's happening with my ticket?".
- Add a KB document for a new topic (e.g. meeting rooms), re-run step 1 and check that step 2 now answers it.
