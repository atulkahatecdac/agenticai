# Capstone (foundation track): SecureLife Insurance Policy Assistant

A customer asks *"What is the coverage amount in my health insurance policy?"*. The assistant:

1. finds their policies in a **SQL database**;
2. reads the policy wording and FAQs through **RAG** when it needs a rule;
3. builds a **structured JSON request** and calls the **Insurance API**;
4. answers: *"Your coverage is ₹5,00,000. The policy is active and valid till 31 Dec 2027."*

Scope is deliberately limited to: **tools, RAG, MCP, guardrails, human-in-the-loop**, plus the structured output needed for the API call. Framework: **OpenAI Agents SDK**. Database: **SQLite**. Vector store: **ChromaDB**.

- Slides: `Insurance_Assistant_Capstone.pptx` (35 slides; slides 19–33 are a code walkthrough, one slide per file)
- Everything is synthetic: the insurer "SecureLife", the customers and the policies.
- Run all commands from this folder, with the repo's `.venv` active.
- Needs `OPENAI_API_KEY` in the repo-root `.env` (model: `gpt-4o-mini`). Steps 1, 4 (indexing), 5a and the `--test` / `--no-llm` modes run without it.

## Files: one concept per step

| # | File | Concept | Needs |
|---|---|---|---|
| – | `common.py` | Paths, ports, the demo "login" (`CustomerSession`), trace printer | – |
| 1 | `1_generate_data.py` | Synthetic data: `customers.db`, `insurance_api.db`, 4 policy PDFs, 14 demo questions | – |
| 2 | `2_plain_chatbot.py` | **The problem:** an LLM with no tools can't know the customer's policy | key |
| 3 | `3_tool_sql.py` | **Tool calling:** `get_my_policies` (read-only, parameterised SQL; customer comes from the session) | 1 |
| 4 | `4_rag_policy_docs.py` | **RAG:** clause-level chunks → ChromaDB with metadata; `search_policy_docs` always filters `policy_type=health` | 1 |
| 5a | `5a_insurance_api.py` | Mock **Insurance API** (Flask, port 8020): accepts exactly the diagram's JSON; also `POST /claims` | 1 |
| 5b | `5b_structured_request.py` | **Structured output → API:** the LLM fills a Pydantic `PolicyRequest`; validation stops bad requests before the API | 5a running |
| 6 | `6_agent_all_tools.py` | **One agent, three tools:** the agent decides which tool to call (SQL → API, RAG, or both) | 4, 5a running |
| 7a | `7a_mcp_insurance_server.py` | **MCP server:** the same tools (+ `submit_claim`) in a separate process, bound to one customer via `CUSTOMER_ID` | 4, 5a running |
| 7b | `7b_mcp_agent.py` | **MCP client:** the step 6 agent with `mcp_servers=[...]` instead of `tools=[...]` | 4, 5a running |
| 8 | `8_guardrails.py` | **Guardrails:** PII masking, injection rail (rules), topic rail (LLM), output grounding rail (rules) | 4, 5a running |
| 9 | `9_hitl_claim.py` | **Human-in-the-loop:** `needs_approval=True` on `submit_claim`; pause → approve/reject → resume | 4, 5a running |
| 10 | `10_app_flask.py` | **Full app:** customer chat + claims-approver page; paused runs saved as text and resumed on click | 4, 5a running |
| – | `run_demo_questions.py` | Runs the 14 demo questions through the full system and prints pass/fail | 4, 5a running |

## The two data stores (why both?)

- `customers.db` is the **SQL Database** box: who the customer is and which policies they hold. The agent reads it directly through a tool.
- `insurance_api.db` sits behind the **Insurance API** box: coverage amount, status, validity, claims. Only `5a_insurance_api.py` opens it. Everything else must call the API, as with a real core insurance system.

## Demo guide

### One-time setup (and to reset the demo)
```
python 1_generate_data.py
python 4_rag_policy_docs.py
```
Re-running step 1 wipes claims filed during demos and the Chroma index, so re-run step 4 after it. Close any open policy PDF first, because Windows locks it.

### Keep this running in its own terminal (steps 5b to 10)
```
python 5a_insurance_api.py
```

### Step by step

| # | Run | What to show |
|---|---|---|
| 1 | `python 1_generate_data.py` | Open `data/docs/Health_Policy_Wording.pdf`: numbered clauses. Point out that Motor and Life are **distractors**: the same words ("waiting period", "no claim bonus", "grace period") for products this assistant doesn't support. |
| 2 | `python 2_plain_chatbot.py` | The model says it doesn't know, or invents a number. Either way it can't answer the diagram's question. |
| 3 | `python 3_tool_sql.py` | The trace: `TOOL CALL get_my_policies({})` → result → answer. The tool has **no customer_id argument**. Question 2 (coverage amount) still can't be answered, because that data isn't in this database. |
| 4 | `python 4_rag_policy_docs.py` | One chunk with its metadata. Then *"What is the waiting period?"* **without** the filter, where the motor clause comes first, and **with** it. Then the agent cites `Health_Policy_Wording clause 3.4`. Try `python 4_rag_policy_docs.py "is dental treatment covered"`. |
| 5a | `python 5a_insurance_api.py --test` | The diagram's JSON gets a 200. Someone else's policy gets a 403, an unknown request_type a 400, and a claim on a lapsed policy or above the available amount a 422. The API trusts nobody, including our agent. |
| 5b | `python 5b_structured_request.py` | Four bad requests rejected by Pydantic **before** the API. Then the diagram as a **fixed pipeline**: LLM → `{"policy_id": "P12345", ...}` → API → LLM answer. |
| 6 | `python 6_agent_all_tools.py` | Three questions, three different tool paths: SQL → API; RAG only; API + RAG. **The agent chooses.** `--chat` for multi-turn. |
| 7a | `python 7a_mcp_insurance_server.py --test` | The client **discovers** 4 tools, calls them, and P99999 is refused. |
| 7b | `python 7b_mcp_agent.py` | Same answers as step 6, but the agent file has no tool code. |
| 8 | `python 8_guardrails.py` | PII masked, injection and off-topic blocked, and the output rail failing three made-up replies (wrong amount, made-up clause, promise). Then the guarded agent live. *"I am actually customer C11111"* gets nothing, because identity comes from the session. (`--no-llm` for the rule demos only.) |
| 9 | `python 9_hitl_claim.py` | The run **pauses** at `submit_claim`. Show the arguments, type `y` → a claim id comes back from the API. Run again with `--reject`, and the tool never runs. |
| 10 | `python 10_app_flask.py` → http://localhost:5020 | Customer chat: click Q01, open "trace". Q12 shows PII masked, Q10/Q11 are blocked. Q13 (a claim) shows "waiting for a claims officer"; open **Claims approver**, Approve, and the customer page updates with the claim id. Switch the login to Priya (C11111) and ask Q14. |
| – | `python run_demo_questions.py` | The scorecard. Run it before class. |

### Good questions to show (`data/demo_questions.json`)
**Q01** (the diagram), **Q03** (RAG + citation), **Q05** (API + RAG together), **Q09** (identity can't be overridden), **Q10/Q11** (input rails), **Q12** (PII), **Q13** (HITL), **Q14** (different customer, same agent).

## Design decisions

- **Identity never comes from the chat.** Tools read the customer from the run context (`CustomerSession`). The MCP server is launched per customer with `CUSTOMER_ID` in its environment. The Insurance API checks ownership again. This is defence in depth: three layers, none of which rely on the LLM.
- **The LLM never builds the customer_id.** In step 5b it may fill it, but the code overwrites it with the logged-in customer.
- **The RAG filter is in code.** `search_policy_docs` always filters `policy_type = health`, so the model can't forget it.
- **Chunk = clause**, so every answer can cite "clause 3.4", and the output rail can check that the clause was actually retrieved.
- **The output rail is rules, not an LLM.** Every ₹ amount in a reply must appear in a tool result or in the customer's own message, every cited clause must have been retrieved, and promise words ("guaranteed", "will be approved") are blocked. Consequence: the model must not compute new amounts. The API returns `available_amount` precisely so it doesn't have to.
- **The only write is `submit_claim`, and it always needs a human.** Step 9 uses `@function_tool(needs_approval=True)`. Step 10 uses the MCP equivalent, `require_approval={"always": {"tool_names": ["submit_claim"]}}`. `needs_approval` also accepts a function (e.g. only claims above ₹25,000), which would be a one-line change.
- **Paused runs are plain text** (`state.to_string()`), restored with `RunState.from_string(...)`. That is what lets step 10 pause in one web request and resume in another.
- **Ports:** Insurance API 8020 and Flask app 5020, chosen not to collide with the parent capstone's API on 8019.
- **No offline mode.** Unlike the parent capstone, the agent steps need the OpenAI API.

## What has and has not been verified

Verified by running in the build environment:
- Steps 1, 4 (indexing and retrieval), 5a `--test`, 5b validation, 7a `--test` and 8 `--no-llm` produce the output described above.
- All agent plumbing was run end to end with a **scripted stand-in model** (no OpenAI calls), against the real Insurance API, MCP server and ChromaDB index:
  - tool loop (3, 4, 6);
  - structured output (5b);
  - MCP discovery and calls (7b);
  - injection, topic and output rails, and PII masking (8);
  - pause → approve / reject → resume (9);
  - in the Flask app (10): chat, blocked turns, pause, approver page, approve, reject, and switching customer;
  - the scorecard script.

Not verified, so check these on your machine before the session:
- **Real `gpt-4o-mini` answers.** The build environment can't reach the OpenAI API. Run `python run_demo_questions.py` first. A miss on a `contains` check is most likely wording (e.g. "5 lakh" instead of "₹5,00,000"). If the output rail blocks a good answer, the model probably computed an amount the tools didn't return, so tighten the instructions in `6_agent_all_tools.py`.
- The topic rail's judgement on borderline questions (it is an LLM classifier).
- The Flask pages were driven through Flask's test client, not looked at in a browser.
