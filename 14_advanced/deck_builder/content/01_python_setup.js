const ASYNC = "01_basic_test/01_2_sync_vs_async_llm_calls_google.py";

module.exports = {
  section: "Module 01 – Python & AI Dev Environment",
  slides: [
    {
      kind: "opener",
      eyebrow: "Module 01",
      title: "Python & AI Dev Environment Setup",
      subtitle: "What an agentic application is made of, and a clean, repeatable Python setup to build one",
      goals: [
        { icon: "FaRobot", title: "Know what an agent is made of", text: "and name the parts of the agentic AI ecosystem" },
        { icon: "FaBoxOpen", title: "Isolate and pin dependencies", text: "venv, pip, requirements.txt and uv" },
        { icon: "FaKey", title: "Keep secrets out of code", text: "API keys in .env, loaded with python-dotenv" },
        { icon: "FaBolt", title: "Make concurrent LLM calls", text: "async, await and asyncio.gather()" },
      ],
      agenda: [
        "The agentic AI ecosystem",
        "Typical agent architecture and Python libraries",
        "Virtual environments",
        "Set up the course repo: Python, VS Code, venv, .env",
        "asyncio for concurrent LLM calls",
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
      title: "Set Up the Course Repo – Windows",
      subtitle: "Windows PowerShell, from a blank machine to a running script – uv also fetches Python 3.12",
      demo: "Repo: github.com/atulkahatecdac/agenticai  ·  README.md → Quick start",
      split: [1.12, 1],
      left: [
        { type: "code", caption: "1. Install uv, Git, VS Code – then reopen the terminal", code:
`winget install astral-sh.uv
winget install Git.Git
winget install Microsoft.VisualStudioCode` },
        { type: "code", caption: "2. Get the code and open it", code:
`mkdir C:\\code; cd C:\\code
git clone https://github.com/atulkahatecdac/agenticai.git
cd agenticai
code .` },
        { type: "code", caption: "3. Create .env", code:
`copy .env.example .env
code .env      # fill in OPENAI_API_KEY=sk-...` },
      ],
      right: [
        { type: "code", caption: "4. venv + packages (VS Code terminal: Ctrl+`)", code:
`uv venv --python 3.12 --seed .venv
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
.venv\\Scripts\\activate
uv pip install -r requirements.txt
# deepeval (optional): README → Quick start, step 2
# never run: uv pip sync (removes packages)` },
        { type: "code", caption: "5. Python extension + interpreter", code:
`code --install-extension ms-python.python
Ctrl+Shift+P → Python: Select Interpreter
→ .\\.venv\\Scripts\\python.exe` },
        { type: "code", caption: "6. Test", code:
`python 2_openai_agents/2_1_openai_agent_basic.py` },
      ],
    },
    {
      title: "Set Up the Course Repo – macOS / Linux",
      subtitle: "Terminal (zsh / bash), from a blank machine to a running script – uv also fetches Python 3.12",
      demo: "Repo: github.com/atulkahatecdac/agenticai  ·  README.md → Quick start",
      split: [1.12, 1],
      left: [
        { type: "code", caption: "1. Install uv, Git, VS Code – then reopen the terminal", code:
`brew install uv git                               # macOS
brew install --cask visual-studio-code
curl -LsSf https://astral.sh/uv/install.sh | sh   # Linux
sudo apt install git; sudo snap install code --classic` },
        { type: "code", caption: "2. Get the code and open it", code:
`mkdir -p ~/code && cd ~/code
git clone https://github.com/atulkahatecdac/agenticai.git
cd agenticai
code .` },
        { type: "code", caption: "3. Create .env", code:
`cp .env.example .env
code .env      # fill in OPENAI_API_KEY=sk-...` },
      ],
      right: [
        { type: "code", caption: "4. venv + packages (VS Code terminal: Ctrl+`)", code:
`uv venv --python 3.12 --seed .venv
source .venv/bin/activate
uv pip install -r requirements.txt
# deepeval (optional): README → Quick start, step 2
# never run: uv pip sync (removes packages)` },
        { type: "code", caption: "5. Python extension + interpreter", code:
`code --install-extension ms-python.python
Cmd/Ctrl+Shift+P → Python: Select Interpreter
→ ./.venv/bin/python` },
        { type: "code", caption: "6. Test", code:
`python 2_openai_agents/2_1_openai_agent_basic.py` },
      ],
    },
    {
      title: "Fallback: Set Up with pip",
      subtitle: "If uv is blocked or misbehaves – the same steps with plain Python and pip (slower, same result)",
      demo: "Repo: github.com/atulkahatecdac/agenticai  ·  README.md → Fallback: plain pip",
      split: [1.12, 1],
      left: [
        { type: "code", caption: "1. Install Python, Git, VS Code – then reopen the terminal", code:
`winget install Python.Python.3.12
winget install Git.Git
winget install Microsoft.VisualStudioCode` },
        { type: "code", caption: "2. Get the code and open it", code:
`mkdir C:\\code; cd C:\\code
git clone https://github.com/atulkahatecdac/agenticai.git
cd agenticai
code .` },
        { type: "code", caption: "3. Create .env", code:
`copy .env.example .env
code .env      # fill in OPENAI_API_KEY=sk-...` },
      ],
      right: [
        { type: "code", caption: "4. venv + packages (VS Code terminal: Ctrl+`)", code:
`py -3.12 -m venv .venv
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
.venv\\Scripts\\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
# deepeval (optional): README → Fallback: plain pip` },
        { type: "code", caption: "5. Python extension + interpreter", code:
`code --install-extension ms-python.python
Ctrl+Shift+P → Python: Select Interpreter
→ .\\.venv\\Scripts\\python.exe` },
        { type: "code", caption: "6. Test", code:
`python 2_openai_agents/2_1_openai_agent_basic.py` },
      ],
    },

    {
      title: "Hello, Agentic AI",
      subtitle: "Your first LangChain call – to a local model, no API key needed",
      demo: "01_basic_test/01_1_hello_agentic_ai.py",
      split: [1, 1.3],
      left: [
        { type: "code", caption: "Once: install Ollama and get the model", code:
`winget install Ollama.Ollama   # Windows
brew install ollama            # macOS
ollama pull qwen3:8b` },
        { type: "code", caption: "Run it", code:
`python 14_advanced/01_basic_test/01_1_hello_agentic_ai.py` },
      ],
      right: [
        { type: "code", caption: "01_1_hello_agentic_ai.py", code:
`from langchain_ollama import ChatOllama

llm = ChatOllama(model="qwen3:8b", reasoning=False)

response = llm.invoke("Say hello to a student starting "
                      "an Agentic AI course, in one sentence.")

print(response.content)` },
        { type: "callout", eyebrow: "reasoning=False", text: "qwen3 is a thinking model – this returns just the answer, without its <think> text." },
      ],
    },

    {
      title: "Same Code, Any Model",
      subtitle: "LangChain hides the provider: change the model line, keep everything else",
      demo: "01_basic_test/: 01_1 (Ollama), 01_2 (Google), 01_3 (OpenAI)",
      blocks: [
        { type: "table", size: 10.5, widths: [1.3, 2.0, 5.0], head: ["Provider", "Package", "The only line that changes"], rows: [
          ["Local – Ollama", "`langchain-ollama`", "`llm = ChatOllama(model=\"qwen3:8b\")`"],
          ["Google – Gemini", "`langchain-google-genai`", "`llm = ChatGoogleGenerativeAI(model=\"gemini-2.5-flash-lite\")`"],
          ["OpenAI", "`langchain-openai`", "`llm = ChatOpenAI(model=\"gpt-4o\")`"],
        ] },
        { type: "code", caption: "The same for all three", code:
`response = llm.invoke("Say hello to a student starting an Agentic AI course.")
print(response.content)` },
      ],
    },
    {
      title: "Reading Text from an Image",
      subtitle: "One message with text and an image – the model reads Hindi, French and Japanese, then translates",
      demo: "01_basic_test/01_3_read_image_and_audio_openai.py",
      split: [1, 1.1],
      left: [
        { type: "image", src: "multilingual_text.png", alt: "The same two sentences about agentic AI in Hindi, French and Japanese" },
        { type: "callout", eyebrow: "gpt-4o, not gpt-4o-mini", text: "mini got the meaning but misread the Hindi letters – for reading text, use the bigger model." },
      ],
      right: [
        { type: "code", caption: "Part 1: the image  (to_base64() reads a file as base64)", code:
`vision_llm = ChatOpenAI(model="gpt-4o")
image_b64 = to_base64("multilingual_text.png")

image_message = HumanMessage(content=[
    {"type": "text", "text": "This image has the same "
        "text in three languages. Write out each one "
        "exactly as written, naming the language, "
        "then give one English translation."},
    {"type": "image_url", "image_url":
        {"url": f"data:image/png;base64,{image_b64}"}},
])
print(vision_llm.invoke([image_message]).content)` },
      ],
    },
    {
      title: "Reading the Same Text from Audio",
      subtitle: "Same pattern, different content block: an audio model transcribes and translates each clip",
      demo: "01_basic_test/01_3_read_image_and_audio_openai.py  ·  hindi.mp3, french.mp3, japanese.mp3",
      split: [1.25, 1],
      left: [
        { type: "code", caption: "Part 2: the audio", code:
`audio_llm = ChatOpenAI(model="gpt-audio-mini")

for file_name in ["hindi.mp3", "french.mp3", "japanese.mp3"]:
    audio_message = HumanMessage(content=[
        {"type": "text", "text": "Write out exactly what is "
            "said in this audio, in its original language "
            "and script, then give an English translation."},
        {"type": "input_audio", "input_audio":
            {"data": to_base64(file_name), "format": "mp3"}},
    ])
    print(audio_llm.invoke([audio_message]).content)` },
      ],
      right: [
        { type: "table", size: 10.5, widths: [1.3, 2.7], head: ["Input", "Content block"], rows: [
          ["Text", "{\"type\": \"text\", ...}"],
          ["Image", "{\"type\": \"image_url\", ...}"],
          ["Audio", "{\"type\": \"input_audio\", ...}"],
        ] },
        { type: "callout", eyebrow: "Model per input", text: "`gpt-4o` reads images; `gpt-audio-mini` listens to audio. The LangChain code around them doesn't change." },
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
      demo: "Concept",
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
        { type: "code", caption: "One LangChain model", code:
`from langchain_google_genai import ChatGoogleGenerativeAI

llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash-lite")` },
        { type: "compare", size: 11, codeSize: 9, cols: [
          { title: "Sync – invoke(), times add up", color: "slate", code:
`for prompt in PROMPTS:
    print(llm.invoke(prompt).content)` },
          { title: "Async – ainvoke(), time of the slowest", color: "teal", code:
`results = await asyncio.gather(
    *(llm.ainvoke(p) for p in PROMPTS))` },
        ] },
      ],
    },
    {
      kind: "summary",
      title: "Module 01 Summary",
      subtitle: "What you set up",
      built: [
        { tag: "venv", title: "An isolated environment", text: ".venv and the repo's pinned requirements" },
        { tag: ".env", title: "Secrets handled properly", text: "Keys in .env, template in .env.example" },
        { tag: "async", title: "Concurrent calls", text: "asyncio.gather() for independent LLM requests" },
      ],
      takeaways: [
        "An agent = an LLM + tools + memory, in a loop, toward a goal",
        "One project, one virtual environment",
        "Pin versions; uv pip install -r requirements.txt",
        "Never commit API keys",
        "Use async when the program spends its time waiting",
      ],
      next: "Module 02: FastAPI, Streamlit and Gradio for AI Apps",
    },
  ],
};
