# Step 7 — MCP Tool Boundary

## Files changed

- `accounts_mcp_server.py`, `transaction_mcp_server.py`, `service_mcp_server.py`
  (new) — one FastMCP stdio server per domain, following
  `6_mcp/6_12_crypto_mcp_server.py`'s shape. Together they hold the same seven
  `@tool` functions that used to live directly in step 6's file, unchanged
  except for where they run.
- `12_2_7_mcp_tool_boundary.py` (new) — the coordinator + specialists, with the
  seven tool implementations removed. This file no longer imports `mock_bank`
  at all — only the three server files do now.

## Architecture change

Following `6_mcp/6_15_langgraph_agent_mcp_tools.py`'s `MultiServerMCPClient`
pattern: Accounts, Transaction, and Service's tool implementations move out of
the agent process into three separate stdio subprocesses. The agent no longer
defines what a tool *does* — it just asks the MCP client what tools each server
*exposes*, and binds whatever comes back:

```python
mcp_client = MultiServerMCPClient({
    "accounts": {"transport": "stdio", "command": sys.executable, "args": [".../accounts_mcp_server.py"]},
    "transaction": {...},
    "service": {...},
})
mcp_tools = load_mcp_tools()  # asyncio.run(mcp_client.get_tools()), cached via st.cache_resource
```

FAQ Agent is untouched — MCP is a tool-calling boundary, and FAQ has no tools,
only a retriever, so there's nothing to move for it.

**A real plumbing consequence, not a bug**: MCP tools from `langchain_mcp_adapters`
are async-only. `make_specialist_agent`'s `agent` node became `async def` (using
`llm_with_tools.ainvoke`), because `ToolNode` picks its sync-vs-async tool-call
path based on whether the *graph* is invoked via `.invoke()` or `.ainvoke()`, and
an async-only tool crashes under the sync path. The coordinator's
`run_specialist` — itself a plain sync function, called synchronously inside
LangGraph's `Send`-dispatch worker thread — now runs every specialist via
`asyncio.run(info["app"].ainvoke(...))` instead of `.invoke(...)`. Each worker
thread getting its own fresh event loop via `asyncio.run()` is safe precisely
*because* `Send` dispatch already runs each specialist in its own OS thread (no
shared/conflicting event loop). The coordinator graph itself is still invoked
synchronously from the Streamlit UI — `coordinator_app.invoke(...)` didn't
change; only the *inner* specialist graphs needed to become async-invokable.
FAQ's plain sync nodes run fine under `.ainvoke()` too (LangGraph executes sync
nodes in a thread pool internally), so one calling convention now covers all
four specialists uniformly.

## Demo prompts

Same four as step 6 - the point of this step is that the *outputs* don't
change, only where the tool code lives:

- `"What is the account balance for customer CUST1001?"` → Accounts Agent,
  round-tripped through `accounts_mcp_server.py`.
- `"What is my balance and show me my last 5 transactions for customer
  CUST1001?"` → Accounts Agent **and** Transaction Agent, two different MCP
  servers hit in parallel via `Send`, in the same superstep.
- `"How do I report a lost debit card?"` → FAQ Agent, unaffected by MCP.
- `"Please update the address for customer CUST1003 to '99 Residency Road,
  Bengaluru'."` → a real write through `service_mcp_server.py`, confirmed to
  actually persist in `bank.db` (not just a plausible-looking reply).

## Expected output

Identical answers to step 6, byte-for-byte in substance - a stronger
regression bar than usual, since this step is explicitly a refactor that
shouldn't change behavior, only the tool boundary.

## Failure case

No functional failure surfaced. What this step actually proves, per the
deck's own framing: `mock_bank.py`'s implementation could change completely
(swap SQLite for a real banking API, say) and only the three server files
would need touching - `12_2_7_mcp_tool_boundary.py` never references
`mock_bank` and would be unaffected. The next gap the deck calls out (slide
9's "next gap") is real and still open: *nothing* here knows *who* is asking -
any customer ID typed into the chat works for any conversation. That's step 8
(authentication + session).

## Regression test

Ran all four step-6 demo prompts against the MCP-backed version - identical
results. Verified headlessly via `streamlit.testing.v1.AppTest`, including the
parallel cross-domain case (two MCP servers called concurrently in the same
`Send` superstep) and a real write (address change) confirmed to persist in
`bank.db` afterward, then reset.

## Run

```
streamlit run 12_2_7_mcp_tool_boundary.py
```

No separate step to start the MCP servers - `MultiServerMCPClient` spawns each
one (`sys.executable <server>.py`) as a stdio subprocess on demand.
