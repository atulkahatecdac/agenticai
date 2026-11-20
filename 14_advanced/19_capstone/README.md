# Module 19: Capstone projects

Independent capstone projects. Each folder is self-contained: its own scripts, data, README and slides. Run every command from inside the project's folder.

| Folder | Project | Track | Stack |
|---|---|---|---|
| [`warranty_returns/`](warranty_returns/) | Warranty & Returns Resolution Assistant (Part 1: build; Part 2: tests, load test, security audit, Docker, CI/CD) | Advanced | LangGraph multi-agent, ChromaDB hybrid RAG, MCP, FastAPI + Streamlit, Prometheus/Grafana, OpenAI (or offline) |
| [`insurance_assistant/`](insurance_assistant/) | SecureLife Insurance Policy Assistant | Foundation | OpenAI Agents SDK: tools, RAG (ChromaDB), structured output, MCP, guardrails, human-in-the-loop, Flask |
| [`it_helpdesk/`](it_helpdesk/) | BrightPath IT Helpdesk Copilot | Intermediate | Fully local: Ollama + LangChain/LangGraph multi-agent, RAG (Chroma), 2 MCP servers, guardrails, human-in-the-loop, SQLite, Flask, LLM-as-judge |
| [`docassist/`](docassist/) | DocAssist: Agentic RAG deployed with Docker Compose (built in small steps, own deck `docassist.pptx`) | Deployment | OpenAI tool-calling agent (no framework), Postgres + pgvector for vectors and short-term memory, FastAPI + Streamlit, Docker Compose (3 containers), cloud VM |

Ports are chosen so the projects can run side by side:

| Project | Ports |
|---|---|
| `warranty_returns` | API 8019, Prometheus 9096, Grafana 3001, containerised UI 8519 |
| `insurance_assistant` | API 8020, app 5020 |
| `it_helpdesk` | app 5021 |
| `docassist` | UI 8522; laptop-only: API 8022, Postgres 5433 (in Compose only 8522 is published) |
| `shopassist` | Docker (14d) 8023; `uvicorn 13a_api_agent:app` on your choice of port |
