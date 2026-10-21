# Agentic AI: course code

Code for the *Agentic AI* course. Every numbered folder is a self-contained playground for one framework or topic, and almost every script is one small demo of one idea. Nothing here is a single application: you run scripts one at a time and read the output.

## Quick start

You need **Python 3.12** (the version the pins are tested on). [Ollama](https://ollama.com) is optional, for the scripts that run local models.

```bash
# 1. Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux

# 2. Install dependencies (see "Installing requirements" below if this fails)
pip install -r requirements.txt

# 3. Add your API keys
copy .env.example .env          # Windows  (cp .env.example .env on macOS/Linux)
#    then edit .env - most demos only need OPENAI_API_KEY

# 4. Run any script
python 2_openai_agents/2_1_openai_agent_basic.py
```

Scripts find their data files relative to their own location, so you can run them from any working directory.

### Installing requirements

`requirements.txt` pins versions that are known to install and import together. Two things to know:

- **`deepeval` clashes with `chromadb`** over the `posthog` version. `pip` usually copes. A strict resolver such as `uv pip install -r requirements.txt` fails outright. If that happens, install everything except the `deepeval` line, then run `pip install deepeval==4.1.5 --no-deps`. After that, install deepeval's remaining dependencies with the one-line command in the comment under `deepeval` in `requirements.txt`. Without them, `import deepeval` fails.
- **LangChain, LangGraph and CrewAI are pinned to their pre-1.0 releases** on purpose, because the scripts use 0.x-era APIs. Don't upgrade them on their own.

Some folders need their **own** virtual environment instead:

| Folder / script | Why |
|---|---|
| `9_general/dspy/` | `dspy` and `crewai` need incompatible `json-repair` versions. Use a separate venv with `pip install dspy`. |
| `17_problems/RAG/1b_pdf_cleanup_with_docling.py` | Docling pulls in PyTorch. Install `langchain-docling==1.1.0` in a separate venv. |
| `12_project/12_1_openai_agents_diet_agent/` | Ships its own `venv/`. |
| `7_n8n/visual-demo/` | Own `requirements.txt` (face recognition stack); setup steps in its README. |
| `14_advanced/19_capstone/*`, `14_advanced/18_Dockerizing/*` | Each project has its own README / requirements / Docker setup. |

> **Never run `pip-sync` / `uv pip sync` against `requirements.txt`.** It lists only top-level packages, so `sync` uninstalls every dependency it doesn't name (torch, transformers, sqlalchemy, ...).

### API keys

[`.env.example`](.env.example) lists every key used anywhere in the repo, grouped by purpose and with the scripts that need it. Copy it to `.env` in the repo root. Most scripts call `load_dotenv(override=True)`, which finds it automatically. The exceptions:

- **AWS Bedrock** (`8_bedrock`) uses your normal AWS credentials (`aws configure`), not `.env`.
- **Google ADK** agents (`11_google_adk/*`) each read a `.env` in their own folder. Copy the `.env.example` that sits next to each agent.

`.env` is git-ignored. Never commit real keys.

## What's in each folder

Files inside a folder are numbered in teaching order (`2_1_...` before `2_2_...`), and later files build on earlier ones.

| Folder | Topic |
|---|---|
| `0_slides` | Main course slide deck |
| `1_openai_chat_requests` | Raw OpenAI Chat Completions / Responses API: streaming, images, PDFs, structured output, a basic chatbot; Gemini and Ollama equivalents |
| `2_openai_agents` | OpenAI Agents SDK: agent patterns (tool use, ReAct, plan-and-execute, reflection, ReWOO, multi-agent), RAG variants, guardrails, memory, Flask front ends |
| `3_langgraph` | LangChain LCEL and LangGraph: memory and checkpointers, guardrails, a banking chatbot built up step by step (Chroma, FAISS, web search, email/ntfy notifications) |
| `4_crewai` | CrewAI multi-agent crews: document generation, log analysis, cloud billing, stock analysis, customer service |
| `5_autogen` | AutoGen: agents, group chats (round robin, selector, magentic), GraphFlow, structured output, multimodal, memory |
| `6_mcp` | Model Context Protocol: paired server/client scripts, OAuth2 progression (`authentication/`), agentic RAG over MCP (`mcp_agentic_rag/`). `6_10_malicious_mcp_*` is a deliberate **attack demo** for security awareness. |
| `7_n8n` | n8n workflow exports (JSON, import into n8n), a Flask bridge to an n8n webhook, Qdrant setup scripts |
| `8_bedrock` | AWS Bedrock: boto3, LangChain integration and RAG, image generation, embeddings |
| `9_general` | Grab-bag: DSPy, SHAP/LIME explainability, LangChain basics, Langfuse observability, Phidata, RAG with Chroma/LlamaIndex/Cohere, production-style app layouts (`prod/`) |
| `10_eval` | Prompt and RAG evaluation (promptfoo configs, prompt regression) |
| `11_google_adk` | Google Agent Development Kit agents (run with the `adk` CLI from this folder) |
| `12_project` | Capstone: a diet agent built up incrementally (basic → streaming → tools → RAG → multi-agent → MCP), and a banking chatbot |
| `13_a2a` | Agent2Agent (A2A) protocol, hand-rolled: a minimal echo agent and a multi-agent trip planner |
| `14_advanced` | Advanced engineering course (deck generated by `deck_builder/`): LLM basics, RAG, LangChain agents, LangGraph (cycles, human-in-the-loop, persistence), LangSmith, deep agents, CrewAI, agentic/graph RAG, n8n, guardrails, monitoring and fine-tuning, Docker, capstones (`19_capstone/`) |
| `15_real` | "Real-world" patterns: agent memory types, adaptive retrieval, grounded generation, RAG evaluation (RAGAS, DeepEval), tracing (LangSmith, Langfuse), voice agents, human-in-the-loop |
| `16_PGP-Agentic` | PGP course: the course deck (generated by `deck_builder/`), session plan, and `code/session_N/` copies of every demo in teaching order |
| `17_problems` | Solutions to non-obvious problems (e.g. PDF headers/footers and tables breaking RAG); see its README |
| `tools` | Repo maintenance scripts: the smoke test below, and `deck_builder/`, the engine that generates the 14_advanced and PGP decks |

Some folders have their own README with more detail: `13_a2a`, `14_advanced/01_agent_demo`, `14_advanced/19_capstone`, `16_PGP-Agentic/code`, `17_problems`, `12_project/12_2_banking_chatbot`.

## Checking that nothing is broken

There is no unit-test suite: each script is verified by running it. To check the whole repo at once without calling any API, run:

```bash
python tools/smoke_test.py               # syntax + hardcoded-path check + every third-party import
python tools/smoke_test.py --no-imports  # fast: syntax + paths only (a couple of seconds)
```

It checks that every `.py` file compiles. It flags hardcoded absolute paths such as `C:\...`. It imports each third-party package the scripts use, each in its own process, so a version upgrade that breaks a package shows up immediately. Run it after changing `requirements.txt` or upgrading anything in the venv.

## Troubleshooting

- **`ModuleNotFoundError`**: the package isn't in your venv. Check that the venv is active. The folder may also need its own environment (see the table above).
- **Auth / 401 errors**: the key that script needs is missing from `.env`. Search `.env.example` for the provider.
- **Ollama connection refused**: start Ollama (`ollama serve`) and pull the model the script names (`ollama pull <model>`).
- **`TypeError: filtered_warn() got an unexpected keyword argument 'skip_file_prefixes'`**: `crewai` was imported before `shap` in the same process. Import `shap` first.
- **Port already in use**: Flask demos use fixed ports. Stop the other demo, or change the `port=` at the bottom of the script.
- **Chroma / FAISS / SQLite folders appear next to scripts**: these are created on first run and are git-ignored. Delete one to force a rebuild.
