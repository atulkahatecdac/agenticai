const M = "01_agent_demo/";
const ASYNC = "../15_real/sync_vs_async_llm_calls_openai.py";

module.exports = {
  section: "Module 01 – Python & AI Dev Environment",
  slides: [
    {
      kind: "opener",
      eyebrow: "Module 01",
      title: "Python & AI Dev Environment Setup",
      subtitle: "What an agentic application is made of, and a clean, repeatable Python setup to build one",
      goals: [
        { icon: "FaRobot", title: "See an agent at work", text: "and name the parts of the agentic AI ecosystem" },
        { icon: "FaBoxOpen", title: "Isolate and pin dependencies", text: "venv, pip, requirements.txt and uv" },
        { icon: "FaKey", title: "Keep secrets out of code", text: "API keys in .env, loaded with python-dotenv" },
        { icon: "FaBolt", title: "Make concurrent LLM calls", text: "async, await and asyncio.gather()" },
      ],
      agenda: [
        "Demo: an agent hunts for a birthday gift",
        "The agentic AI ecosystem",
        "Typical agent architecture and Python libraries",
        "Virtual environments and dependency management",
        "Managing API keys with .env",
        "Git: clone, branch, commit",
        "asyncio for concurrent LLM calls",
      ],
    },
    {
      title: "Demo: The Birthday Gift Hunt",
      subtitle: "Dad has hidden Mom's gift and left a trail of sticky notes – an AI agent searches the house on its own",
      demo: "streamlit run " + M + "app.py   (Replay mode needs no Ollama)",
      split: [1, 1.1],
      left: [
        { type: "text", text: "**What you see on screen**", size: 12 },
        { type: "icons", d: 0.4, items: [
          { icon: "FaHouse", title: "A floor plan of the house", text: "The robot walks room to room and leaves a numbered trail" },
          { icon: "FaCommentDots", title: "A thought bubble", text: "The agent's own reason for every step, in plain words" },
          { icon: "FaNoteSticky", title: "A board of what it found", text: "Real clues, a brother's prank, last year's note, decoy gifts" },
        ] },
      ],
      right: [
        { type: "text", text: "**The agent can only do three things**", size: 12 },
        { type: "steps", size: 10.5, items: [
          { title: "Walk into a room or look at a spot", text: "and read what is there" },
          { title: "Peek through a door", text: "to see where it leads" },
          { title: "Say where the gift is", text: "and prove it – a wrong guess is rejected" },
        ] },
        { type: "callout", eyebrow: "The point", text: "Nobody wrote the route. The model chooses every step – and each run can go differently." },
      ],
    },
    { kind: "image", src: "agent_trip_workflow.png", alt: "What an agent does: understand, plan, use tools, use memory, collaborate, learn, deliver", demo: "Concept" },
    {
      title: "The Agentic AI Ecosystem",
      subtitle: "The major components – most of them get a module of their own in this course",
      demo: "Concept",
      blocks: [
        { type: "table", size: 10, widths: [1.7, 2.6, 3.4], head: ["Component", "Purpose", "Examples"], rows: [
          ["Foundation models", "Reasoning and language understanding", "GPT-5, Claude, Gemini, Llama"],
          ["Agent frameworks", "Build AI agents", "OpenAI Agents SDK, LangGraph, CrewAI, AutoGen"],
          ["Tools and APIs", "Perform external actions", "Weather API, Gmail, SQL database, GitHub"],
          ["MCP servers", "Standard access to tools and data", "Filesystem, PostgreSQL, GitHub, Tavily"],
          ["A2A protocol", "Agent-to-agent communication", "Multi-agent collaboration"],
          ["Memory", "Conversation and long-term knowledge", "ChromaDB, FAISS, Redis"],
          ["Workflow automation", "Orchestrate business processes", "n8n, Make, Zapier"],
          ["Vector databases", "Semantic document retrieval", "Pinecone, Weaviate, ChromaDB"],
          ["Observability", "Debugging and monitoring", "LangSmith, OpenTelemetry"],
        ] },
      ],
    },
    {
      title: "Typical Agent Architecture",
      subtitle: "Python code in the middle, calling an LLM, memory and tools until it can answer",
      demo: "Concept",
      split: [1, 1.05],
      left: [
        { type: "tree", boxW: 1.25, size: 10.5, rows: [["User request"], [{ label: "Agent (Python)", fill: "navy" }], ["LLM", "Memory / RAG", "Tools"], [{ label: "Final response", fill: "teal" }]] },
      ],
      right: [
        { type: "table", size: 10, widths: [1.5, 2.6], head: ["Area", "Popular libraries"], rows: [
          ["LLM APIs", "OpenAI, Anthropic, Google GenAI"],
          ["Agents", "OpenAI Agents SDK, LangGraph, CrewAI, AutoGen"],
          ["MCP", "MCP Python SDK, FastMCP"],
          ["RAG", "LangChain, LlamaIndex"],
          ["Vector stores", "ChromaDB, Pinecone, FAISS"],
          ["Data", "pandas, NumPy"],
          ["Web APIs", "FastAPI, Flask"],
          ["Plumbing", "requests, asyncio"],
        ] },
      ],
    },

    // ---------------------------------------------------------------- environment
    {
      title: "Virtual Environments",
      subtitle: "An isolated Python with its own interpreter, packages and versions – one per project",
      demo: "Terminal: uv venv  ·  .venv\\Scripts\\activate",
      split: [1.1, 1],
      left: [
        { type: "tree", boxW: 1.45, size: 10.5, rows: [[{ label: "System Python", fill: "navy" }], ["Project A  ·  .venv", "Project B  ·  .venv", "Project C  ·  .venv"], ["openai 2.x, requests", "openai 1.x, flask", "pandas 2.x, numpy"]] },
      ],
      right: [
        { type: "compare", size: 10.5, cols: [
          { title: "Without a venv", color: "slate", items: ["Projects fight over package versions", "An upgrade for one breaks another", "The system Python gets cluttered"] },
          { title: "With a venv", color: "teal", items: ["Each project has its own dependencies", "Different versions side by side", "Reliable dev, test and deploy"] },
        ] },
      ],
    },
    {
      title: "Managing Dependencies",
      subtitle: "Install, record and reproduce the exact packages a project needs",
      demo: "Terminal: uv pip install -r requirements.txt",
      split: [1, 1.15],
      left: [
        { type: "table", size: 10.5, widths: [1.4, 2.6], head: ["Tool", "Purpose"], rows: [
          ["pip", "Install and manage packages"],
          ["requirements.txt", "Record dependencies and versions"],
          ["venv", "Create isolated environments"],
          ["uv", "Fast drop-in replacement for pip, pip-tools and virtualenv"],
        ] },
        { type: "callout", eyebrow: "In this repo", text: "Install with `uv pip install -r requirements.txt`. Never `uv pip sync` – it uninstalls everything that isn't listed." },
      ],
      right: [
        { type: "code", caption: "pip", code:
`pip install openai requests python-dotenv
pip install --upgrade openai
pip uninstall openai
pip install -r requirements.txt` },
        { type: "code", caption: "uv", code:
`# install (Windows PowerShell)
irm https://astral.sh/uv/install.ps1 | iex
uv venv                      # create .venv
.venv\\Scripts\\activate       # activate it
uv pip install -r requirements.txt` },
      ],
    },
    {
      title: "Keeping API Keys Out of Code",
      subtitle: "OpenAI, Anthropic, Google, Tavily, GitHub, Pinecone … every service needs a secret",
      demo: "Repo root: .env (your keys)  ·  .env.example (the template to copy)",
      split: [1, 1.1],
      left: [
        { type: "icons", d: 0.4, items: [
          { icon: "FaTriangleExclamation", title: "Hard-coded keys leak", text: "Into git history, screenshots and shared notebooks", color: "coral" },
          { icon: "FaFileShield", title: "Put them in .env", text: "One file in the repo root, listed in .gitignore" },
          { icon: "FaFileLines", title: "Commit .env.example", text: "The same keys with empty values – a template for everyone else" },
        ] },
      ],
      right: [
        { type: "code", caption: ".env", code:
`OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
TAVILY_API_KEY=tvly-xxxxxxxxxxxx
DATABASE_URL=postgresql://user:password@localhost/db` },
        { type: "code", caption: "Load it at run time", code:
`import os
from dotenv import load_dotenv

load_dotenv(override=True)
api_key = os.getenv("OPENAI_API_KEY")` },
      ],
    },
    {
      title: "Git: Clone, Branch, Commit",
      subtitle: "A distributed version control system that tracks every change and lets people collaborate",
      demo: "Terminal: git clone https://github.com/atulkahatecdac/agenticai.git",
      split: [1, 1.15],
      left: [
        { type: "bullets", size: 11.5, items: [
          "Track code changes over time",
          "Restore earlier versions",
          "Experiment on a branch without touching main",
          "Collaborate with other developers",
          "Work on several features at once",
        ] },
        { type: "callout", eyebrow: ".gitignore", text: "List what must never be committed: `.env`, virtual environments, caches, databases, temporary files." },
      ],
      right: [
        { type: "code", caption: "The everyday commands", code:
`git clone https://github.com/atulkahatecdac/agenticai.git
cd agenticai

git switch -c my-feature     # new branch
git status                   # what changed?
git add app.py
git commit -m "Add the summarise endpoint"
git push -u origin my-feature` },
      ],
    },

    // ---------------------------------------------------------------- asyncio
    {
      title: "asyncio: Stop Waiting in Line",
      subtitle: "AI apps spend most of their time waiting – on LLMs, web searches, databases, MCP tools, file transfers",
      demo: ASYNC,
      split: [1, 1.2],
      left: [
        { type: "text", text: "Asynchronous code lets many **I/O-bound** tasks wait at the same time instead of one after another – better responsiveness and throughput." },
        { type: "callout", eyebrow: "Not for CPU work", text: "asyncio helps when the program is waiting. Heavy computation still needs processes or threads." },
      ],
      right: [
        { type: "table", size: 10.5, widths: [1.5, 3], head: ["Concept", "Purpose"], rows: [
          ["async def", "Define a coroutine (an asynchronous function)"],
          ["await", "Wait for an operation without blocking the loop"],
          ["asyncio.run()", "Start the event loop"],
          ["asyncio.gather()", "Run tasks concurrently; results come back in task order"],
          ["create_task()", "Schedule a task to run in the background"],
        ] },
      ],
    },
    { kind: "image", src: "sync_vs_async_timing.png", alt: "Sync vs async: total time 15 s vs 6 s", demo: ASYNC },
    {
      title: "Sync vs Async in Code",
      subtitle: "Three tasks that each wait 5 seconds: 15 seconds one by one, 5 seconds together",
      demo: ASYNC,
      blocks: [
        { type: "compare", size: 11, codeSize: 9, cols: [
          { title: "Synchronous – about 15 s", color: "slate", items: ["Each call blocks until it finishes"], code:
`def greet_sync(name):
    print(f"{name}: Hello World")
    time.sleep(5)

greet_sync("Task 1")
greet_sync("Task 2")
greet_sync("Task 3")` },
          { title: "Asynchronous – about 5 s", color: "teal", items: ["The waits overlap"], code:
`async def greet_async(name):
    print(f"{name}: Hello World")
    await asyncio.sleep(5)

async def main():
    await asyncio.gather(greet_async("Task 1"),
        greet_async("Task 2"), greet_async("Task 3"))
asyncio.run(main())` },
        ] },
      ],
    },
    {
      title: "Concurrent LLM Calls",
      subtitle: "Independent prompts don't need to queue – send them together with gather()",
      demo: ASYNC,
      blocks: [
        { type: "code", caption: "One helper, used two ways", code:
`client = AsyncOpenAI()

async def call_llm(prompt):
    response = await client.responses.create(model="gpt-5", input=prompt)
    return response.output_text` },
        { type: "compare", size: 11, codeSize: 9, cols: [
          { title: "Sequential – times add up", color: "slate", code:
`r1 = await call_llm("Summarize...")
r2 = await call_llm("Translate...")
r3 = await call_llm("Classify...")` },
          { title: "Concurrent – time of the slowest", color: "teal", code:
`results = await asyncio.gather(
    call_llm("Summarize this article"),
    call_llm("Translate to French"),
    call_llm("Extract keywords"))` },
        ] },
      ],
    },
    {
      kind: "summary",
      title: "Module 01 Summary",
      subtitle: "What you set up and saw",
      built: [
        { tag: "01", title: "A live agent", text: "The gift hunt: tools, decisions and decoys, all local" },
        { tag: "venv", title: "An isolated environment", text: "uv venv and the repo's pinned requirements" },
        { tag: ".env", title: "Secrets handled properly", text: "Keys in .env, template in .env.example" },
        { tag: "async", title: "Concurrent calls", text: "asyncio.gather() for independent LLM requests" },
      ],
      takeaways: [
        "An agent = an LLM + tools + memory, in a loop, toward a goal",
        "One project, one virtual environment",
        "Pin versions; install with pip / uv, never sync",
        "Never commit API keys",
        "Use async when the program spends its time waiting",
      ],
      next: "Module 02: FastAPI, Streamlit and Gradio for AI Apps",
    },
  ],
};
