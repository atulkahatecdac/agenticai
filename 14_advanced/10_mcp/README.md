# Module 10 – Model Context Protocol: Architecture & Custom Servers

Demos for module 10 of the advanced deck, in teaching order. They are copies of `6_mcp/` scripts, renamed for this
module. 10_2 and 10_5 go further than their originals. Each client launches its own server as a stdio subprocess, so
you only run the client, for example `python 14_advanced/10_mcp/10_2_crypto_mcp_client.py`.

| # | Scripts | Syllabus item | Needs |
|---|---|---|---|
| 10_1 | `10_1_weather_mcp_server.py`, `10_1_weather_mcp_client.py` | Scaffolding and connecting a first custom server | – |
| 10_2 | `10_2_crypto_mcp_server.py`, `10_2_crypto_mcp_client.py` | A live data API (CoinGecko) as a **resource** (`crypto://price/{coin}`) and as a tool | – |
| 10_3 | `10_3_database_mcp_server.py`, `10_3_database_mcp_client.py` | Tool discovery; debugging with the **MCP Inspector**; **Claude Desktop** integration | Node.js for the Inspector |
| 10_4 | `10_4_prompt_template_mcp_server.py`, `10_4_prompt_template_mcp_client.py` | Prompts as a primitive, plus a grounding tool | `OPENAI_API_KEY` |
| 10_5 | `10_5_secure_mcp_server.py`, `10_5_secure_mcp_client.py` | **Permission checks** (role set by the host via `MCP_CLIENT_ROLE`) and **input validation** (SQL injection) | – |
| 10_6 | `10_6_malicious_mcp_server.py`, `10_6_malicious_mcp_client.py` | Awareness demo: a "harmless" server with hidden side effects. It **writes `secret_log.txt` and `you_got_pranked.txt` into your home folder**, so delete them afterwards | – |

Debug any server in the Inspector:

```
mcp dev 14_advanced/10_mcp/10_3_database_mcp_server.py
```

To register a server in Claude Desktop, run `mcp install <server>.py`, or add it under `mcpServers` in
`claude_desktop_config.json`.

Module 11 (MCP ecosystem) continues in `../11_mcp_advanced/`.
