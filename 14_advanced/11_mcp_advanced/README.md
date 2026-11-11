# Module 11 – MCP: Ecosystem Integrations

Demos for module 11 of the advanced deck, in slide order. They are copies of `6_mcp/` scripts, renamed for this module.
Run each one from anywhere, for example `python 14_advanced/11_mcp_advanced/11_10_sqlite_to_filesystem_report_pipeline.py`.

| # | Script(s) | Syllabus item | Needs |
|---|---|---|---|
| 11_1 | `11_1_sqlite_resource_mcp_client.py` | SQLite MCP (official `mcp-server-sqlite`): tools and the `memo://insights` resource | – |
| 11_2 | `11_2_filesystem_mcp_client.py` | Filesystem MCP, sandboxed to `fs_sandbox/` (reading outside it is refused) | Node.js (`npx`) |
| 11_3 | `11_3_github_mcp_readonly_client.py` | GitHub MCP (official, in Docker), read-only | Docker, `GITHUB_READONLY_TOKEN` |
| 11_4 | `11_4_github_mcp_write_client.py` | GitHub MCP write tools on a throwaway repo. The deck also shows the Claude Desktop config for this server | Docker, `GITHUB_WRITE_TOKEN`, `GITHUB_DEMO_OWNER/REPO` |
| 11_5 | `11_5_playwright_mcp_gold_price_client.py` | Playwright MCP: extract a price from a rendered page | Node.js |
| 11_6 | `11_6_playwright_mcp_login_demo_client.py` | Playwright MCP: fill and submit a login form | Node.js |
| 11_7 | `11_7_langchain_agent_mcp_tools.py`, `11_7_2_crypto_forex_agent_flask.py` | MCP tools in a LangChain agent (hand-rolled `bind_tools` loop); `_2` adds a Flask UI | `OPENAI_API_KEY`, `EXCHANGE_RATE_API_KEY` |
| 11_8 | `11_8_langgraph_agent_mcp_tools.py` | **MCP + LangGraph**: `MultiServerMCPClient` and a ReAct agent | `OPENAI_API_KEY`, `EXCHANGE_RATE_API_KEY` |
| 11_9 | `11_9_crewai_mcp_tools.py` | **MCP + CrewAI**: MCP tools wrapped as CrewAI `BaseTool`s | `OPENAI_API_KEY`, `EXCHANGE_RATE_API_KEY` |
| 11_10 | `11_10_sqlite_to_filesystem_report_pipeline.py` | **Multi-MCP chaining**: SQLite MCP → filesystem MCP report (no LLM), from `datasets/superstore.csv` into `reports/` | Node.js |

Supporting files:

- `crypto_mcp_server.py` (CoinGecko, no key) and `forex_mcp_server.py` (`EXCHANGE_RATE_API_KEY`) are the two servers
  that 11_7, 11_8 and 11_9 give to their agents.
- `authentication/version_1` → `version_2` → `version_3` is the "MCP in production" slide: a Tavily-search MCP server
  with no auth, then a static Bearer token, then real OAuth2 tokens from Scalekit (`TAVILY_API_KEY`, plus
  `MCP_ACCESS_TOKEN` for v2 and the `SCALEKIT_*` settings for v3).
