# 6_mcp — Model Context Protocol demos

Numbered in teaching order. The order follows modules 10 (MCP) and 11 (MCP ecosystem) of the advanced deck
(`14_advanced/Agentic AI - Advanced Engineering.pptx`). The deck itself uses renamed copies in `14_advanced/10_mcp/`
(module 10) and `14_advanced/11_mcp_advanced/` (module 11), so a fix here may need repeating there. Run each script from anywhere, for example
`python 6_mcp/6_2_database_mcp_client.py`. Clients launch their own server as a subprocess.

| # | Script(s) | What it shows | Needs |
|---|---|---|---|
| 6_1 | `6_1_weather_mcp_server.py`, `6_1_weather_mcp_client.py` | Hello world: one `FastMCP` tool, one stdio client | – |
| 6_2 | `6_2_database_mcp_server.py`, `6_2_database_mcp_client.py` | A server with state (SQLite); client discovers tools (`list_tools`), then calls them. Also used with Claude Desktop | – |
| 6_3 | `6_3_prompt_template_mcp_server.py`, `6_3_prompt_template_mcp_client.py` | MCP **prompts** (server-owned templates) plus a grounding tool | `OPENAI_API_KEY` |
| 6_4 | `6_4_sql_injection_mcp_server.py`, `6_4_sql_injection_mcp_client.py` | A tool that builds SQL from model input: the attack, then the validated version | – |
| 6_5 | `6_5_malicious_mcp_server.py`, `6_5_malicious_mcp_client.py` | **Attack demo**: a "harmless" server with a hidden side effect. Never use it as a template | – |
| 6_6 | `6_6_sqlite_resource_mcp_client.py` | Official reference SQLite server (`mcp-server-sqlite`), tools and resources | – |
| 6_7 | `6_7_filesystem_mcp_client.py` | Official filesystem server, sandboxed to `fs_sandbox/` | Node.js (`npx`) |
| 6_8 | `6_8_github_mcp_readonly_client.py` | GitHub's official server, read-only, against `octocat/Hello-World` | Docker, `GITHUB_READONLY_TOKEN` |
| 6_9 | `6_9_github_mcp_write_client.py` | Same server, write tools, against a throwaway repo | Docker, `GITHUB_WRITE_TOKEN`, `GITHUB_DEMO_OWNER/REPO` |
| 6_10 | `6_10_playwright_mcp_gold_price_client.py` | Official Playwright server reads a price off a rendered page | Node.js |
| 6_11 | `6_11_playwright_mcp_login_demo_client.py` | Playwright fills and submits a login form | Node.js |
| 6_12 | `6_12_crypto_mcp_server.py`, `6_12_crypto_mcp_client.py` | A server wrapping a real public API (CoinGecko) | – |
| 6_13 | `6_13_forex_mcp_server.py` | Exchange-rate server, used by 6_14, 6_15 and 6_17 | `EXCHANGE_RATE_API_KEY` |
| 6_14 | `6_14_langchain_agent_mcp_tools.py`, `6_14_2_crypto_forex_agent_flask.py` | An LLM agent (hand-rolled `bind_tools` loop) choosing between the 6_12 and 6_13 servers; `_2` adds a Flask UI | `OPENAI_API_KEY` |
| 6_15 | `6_15_langgraph_agent_mcp_tools.py` | The same tools through `MultiServerMCPClient` and a LangGraph ReAct agent | `OPENAI_API_KEY` |
| 6_16 | `6_16_sqlite_to_filesystem_report_pipeline.py` | Two official servers chained into a report pipeline (no LLM) | Node.js |
| 6_17 | `6_17_trip_planner_mcp_app.py`, `6_17_weather_mcp_server.py`, `6_17_serp_search_mcp_server.py` | Flask app calling four MCP servers in one workflow: weather (Open-Meteo, real data, no key), Google search via SerpApi, 6_13 forex, filesystem | `SERPAPI_API_KEY`, `EXCHANGE_RATE_API_KEY`, Node.js |
| 6_18 | `6_18_crewai_mcp_tools.py` | The same tools in a CrewAI crew, through a small hand-written MCP→`BaseTool` bridge | `OPENAI_API_KEY`, `EXCHANGE_RATE_API_KEY` |

Subfolders:

- `authentication/` — OAuth2 progression for a Tavily-search MCP server: `version_1` no auth, `version_2` static
  Bearer token, `version_3` Scalekit-issued OAuth2 tokens.
- `mcp_agentic_rag/` — company-policy assistant: an MCP server with no reasoning, over Chroma, plus a LangGraph agent
  on Ollama.
- `mf_nav/` — Indian mutual fund NAV history and forecasting over MCP with a Flask UI (no LLM). See its README.
