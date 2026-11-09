# 12_2 Banking Chatbot — Agentic AI Build Plan

Source: `Banking-Agentic-AI.pptx` in this folder — a 20-slide "problem → solution"
narrative that grows a banking multi-agent system one layer at a time (slide 19's
"10-Step Incremental Build Sequence" is the canonical roadmap; slides 3-18 give the
architecture, demo prompt, and failure case behind each step).

Framework: **LangChain + LangGraph** (not the OpenAI Agents SDK used by the sibling
`12_1_openai_agents_diet_agent`). This repo already has strong precedent for every
piece of this build under `14_advanced/07_langgraph/`, `14_advanced/08_langgraph_cycles_HIL_persistence/`,
`14_advanced/09_langsmith/`, `6_mcp/`, and `3_langgraph/` — each step below names the
existing file it follows so the pattern stays consistent with the rest of the repo
instead of inventing a new style.

One deviation from the deck: **RAG was a missing piece.** The deck's six banking
tools only cover structured, per-customer data (balance, transactions, address,
cheque book, KYC). Slide 2's own framing — "the app already knows the answer,
distributed across 14 screens" — is exactly the shape of a general-knowledge FAQ
problem (how do I open an account, what's the loan process, lost-card policy...),
which structured tools can't answer and shouldn't try to. So this plan inserts a
dedicated RAG-backed FAQ specialist (step 5 below, ChromaDB via `langchain_chroma`)
that the coordinator can route to alongside the tool-calling specialists.
`14_advanced/07_langgraph/07_5_message_graph_bank_faq.py` already builds exactly this
against `3_langgraph/Dataset_Banking_chatbot.csv` — step 5 follows that pattern
directly. Kept at step 5 rather than pulled into steps 3/4: those steps exist to
demonstrate the "one unscoped agent" and "specialist split" problems specifically
for the six *structured* banking tools — folding in a RAG corpus now would blur
that narrative. Say the word if you'd rather have it earlier.

## Steps

Each step is its own subdirectory `12_2_N_<slug>/`, building on the previous step.
Steps 1-2 are plain console scripts; **from step 3 onward the UI is Streamlit**
(`streamlit==1.63.0`, added to root `requirements.txt`). Step 3 has a sidebar of
one-click demo/regression buttons; step 4 onward dropped the sidebar for
simplicity — a plain chat window, type the prompts directly into the chat box.
This replaces the earlier plan of staying console-only until a step-11 Flask
front end. No test suite exists in this repo — verify each step by running it
(console: read stdout; Streamlit: click/type through the UI, or drive it
headlessly with `streamlit.testing.v1.AppTest`), then re-run every prior step's
demo prompts against the new code (regression check) before moving on.

1. **`12_2_1_simple_chat/`** — Naive agent: a single LangGraph node wrapping a bare
   `ChatOpenAI` call. No tools, no RAG, no memory. Demo: "What is my account
   balance?" → the agent must admit it can't access bank data. Establishes the
   baseline gap the rest of the build closes. *(slides 3-4)*

2. **`12_2_2_single_tool/`** — Add one `@tool`-decorated Balance Enquiry function
   bound to the LLM (`llm.bind_tools`), backed by an in-memory mock bank module
   introduced here and reused by every later step. Demo: the same balance question
   now returns real (mock) data. Proves the tool-call loop end-to-end.

3. **`12_2_3_multiple_tools/`** — Expose all six tools (Balance Enquiry, Transaction
   Details, Statement Request, Change of Address, Cheque Book Request, KYC Update)
   on one agent/graph node. Deliberately surface the "too much access" problem: one
   agent has unrestricted access to every domain, no least-privilege boundary. This
   step's README ends on that problem, not a fix. *(slides 5-6)*

4. **`12_2_4_specialist_agents/`** — Split into Accounts / Transaction / Service
   specialist nodes, each with its own scoped tools and system prompt. Demo proves
   domain isolation; surfaces the next problem — who routes a cross-domain question
   like "balance AND last 5 transactions"? *(slide 7)*

5. **`12_2_5_rag_faq_agent/`** — Add a fourth specialist: a RAG-backed FAQ/Knowledge
   agent over `3_langgraph/Dataset_Banking_chatbot.csv` (Chroma + HuggingFace
   embeddings), following `14_advanced/07_langgraph/07_5_message_graph_bank_faq.py`.
   Demo: "How do I report a lost debit card?" is answered from the FAQ corpus, not
   hallucinated. **The missing piece the original deck-only plan skipped.** This
   step also replaces step 4's manual specialist picker with an internal router
   (structured-output classification, following
   `14_advanced/07_langgraph/07_4_conditional_routing_specialists.py`) that picks ONE
   specialist per turn automatically, in one shared chat — no sidebar, no
   dropdown. A cross-domain request still only gets one specialist's partial
   answer; splitting a request across *multiple* specialists is step 6's job.

6. **`12_2_6_coordinator_agent/`** — Extend step 5's router to dispatch to *more
   than one* specialist in the same turn when a request needs it — parallel
   dispatch for multi-domain requests — and synthesize the merged response. First
   architecture that handles real mixed queries ("balance AND last 5
   transactions") end-to-end in one turn. *(slide 8)*

7. **`12_2_7_mcp_tool_boundary/`** — Move each specialist's tool implementations
   behind MCP servers, following `6_mcp/6_22_langgraph_agent_mcp_tools.py`. Proves
   tool changes no longer require agent code changes. *(slide 9)*

8. **`12_2_8_auth_and_session/`** — Two things land together, as they do in the deck:
   (a) identity/token propagation from a mock IdP through the coordinator to every
   specialist, blocking cross-account access; (b) a LangGraph checkpointer-backed
   session store (`SqliteSaver`, following `3_langgraph/3_4_langgraph_memory.py` and
   `14_advanced/08_langgraph_cycles_HIL_persistence/08_3_sqlite_checkpointing_crash_recovery.py`)
   so the agent stops forgetting prior turns. *(slides 10-11)*

9. **`12_2_9_pii_redaction/`** — A regex/pattern-based redaction layer intercepting
   card numbers, account numbers, OTPs, and national IDs before they reach the LLM,
   session history, or logs. Demo: a social-engineering prompt asking for a card
   number + OTP shows `[CARD_XXXX]`-style tokens everywhere downstream. *(slide 12)*

10. **`12_2_10_eval_and_observability/`** — A baseline eval suite (the deck's four
    canonical prompts: balance / last-5-transactions / balance+transactions /
    address-change, checked for correct routing + tool selection) plus LangSmith
    tracing, following `14_advanced/09_langsmith/09_2_trace_langgraph_agent_end_to_end.py`.
    Demo failure case: a stale-cache balance discrepancy, found via trace.
    *(slides 13-14)*

11. **`12_2_11_cost_and_infra/`** — Token/tool-call cost accounting per interaction
    type, a circuit breaker on the model API (must fail as "service unavailable,"
    never hallucinate a balance), and the final end-to-end demo wiring everything
    together (slide 18's architecture) into the Streamlit UI carried forward from
    step 3. *(slides 15-16, 18)*

Slide 17 (security recap) isn't a separate build step — it's a checklist mapping
each control above back to the step that introduced it; worth a final pass once
step 11 is done, not its own subdirectory.

## Shared conventions across steps

- Root `.env` / `load_dotenv(override=True)` for `OPENAI_API_KEY`, matching every
  other script in this repo.
- `sys.stdout.reconfigure(encoding="utf-8")` near the top of the console-only
  scripts (steps 1-2), matching `14_advanced/07_langgraph/*.py` — Windows' cp1252
  console otherwise crashes on the ₹/arrow/checkmark characters LLM output tends
  to contain. Not needed from step 3 onward — Streamlit renders to the browser,
  not the console, so there's nothing for cp1252 to crash on.
- Mock bank data lives in one shared module, `mock_bank.py` (introduced in step 2,
  imported by every later step) rather than being redefined per step. It's
  SQLite-backed (`bank.db`, stdlib `sqlite3`, auto-created and seeded on first
  import) rather than an in-memory dict, so state persists across runs the way a
  real banking backend would — `mock_bank.reset_db()` wipes it back to seed values.
- Run command: `python 12_2_N_<slug>/<script>.py` for steps 1-2 (console);
  `streamlit run 12_2_N_<slug>/<script>.py` for step 3 onward.
