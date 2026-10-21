const S = "session_1/";

module.exports = {
  section: "Session 1 – Agentic AI Foundations",
  slides: [
    {
      kind: "opener",
      eyebrow: "Session 1  ·  Sat 24-Oct  ·  08:00–11:00 AM",
      title: "Agentic AI Foundations and Agent Architectures",
      subtitle: "What agents are, how they are built, and the patterns behind them – using the OpenAI Agents SDK",
      goals: [
        { icon: "FaLightbulb", title: "Explain what an AI agent is", text: "and how it differs from an LLM, a chatbot and a workflow" },
        { icon: "FaScrewdriverWrench", title: "Build agents with the OpenAI Agents SDK", text: "instructions, tools, and the Runner that executes them" },
        { icon: "FaBolt", title: "Run agents sync and async", text: "and know when concurrency pays off" },
        { icon: "FaShapes", title: "Recognise the core design patterns", text: "tool use, ReAct, plan-and-execute, reflection, multi-agent" },
      ],
      agenda: [
        "What an AI agent is and why we need one",
        "Chatbots vs workflows vs agents",
        "Agent components and architecture",
        "Setup and API key",
        "OpenAI Agents SDK basics",
        "Giving an agent tools (@function_tool)",
        "Building a multi-tool agent step by step",
        "Sync vs async agents",
        "Agent design patterns",
        "Agentic AI framework landscape",
      ],
    },

    // ---------------------------------------------------------------- what an agent is
    {
      title: "What Is an AI Agent?",
      subtitle: "A system that uses AI models to perceive, decide and act toward a goal",
      demo: S + "1_1_my_first_agent.py (teaser)",
      blocks: [
        { type: "cards", size: 11, items: [
          { icon: "FaEye", title: "Perception", lines: ["Takes input from its environment", "**e.g.** text, user queries, images, audio, sensor data"] },
          { icon: "FaBrain", title: "Reasoning", lines: ["Decides what to do using rules, logic or ML", "**e.g.** plan a route, pick the best response"] },
          { icon: "FaHandPointer", title: "Action", lines: ["Performs tasks based on its decisions", "**e.g.** answer a question, run a command, call an API"] },
          { icon: "FaChartLine", title: "Learning", lines: ["Optional: improves over time from feedback", "**e.g.** refine recommendations, improve accuracy"] },
        ] },
        { type: "callout", eyebrow: "In one line", text: "An LLM generates text. An agent wraps an LLM with goals, tools and a loop, so it can actually get things done." },
      ],
    },
    { kind: "image", src: "what_is_llm.png", alt: "What is an LLM?", demo: "Concept" },
    { kind: "image", src: "llm_alone_vs_agentic.png", alt: "LLM alone is limited; an agentic application is the complete solution", demo: "Concept" },
    { kind: "image", src: "ml_dl_genai_agentic.png", alt: "Machine learning, deep learning, generative AI and agentic AI compared", demo: "Concept" },
    { kind: "image", src: "three_core_distinctions.png", alt: "Agentic system vs workflow vs autonomous agent", demo: "Concept" },
    {
      title: "The Building Blocks of Agentic AI",
      subtitle: "Every agent we build in this course combines some of these",
      demo: "Concept",
      blocks: [
        { type: "tiles", cols: 4, items: [
          { icon: "FaComment", title: "Instructions", text: "Goal and role in plain language" },
          { icon: "FaMicrochip", title: "LLM", text: "The reasoning engine" },
          { icon: "FaScrewdriverWrench", title: "Tool calling", text: "APIs, code, databases" },
          { icon: "FaArrowsRotate", title: "Think – act – review", text: "The agent loop" },
          { icon: "FaBook", title: "RAG", text: "Grounding in your own documents" },
          { icon: "FaPlug", title: "MCP", text: "A standard way to plug in tools" },
          { icon: "FaMemory", title: "Memory", text: "Short-term and long-term context" },
          { icon: "FaUserCheck", title: "Human-in-the-loop", text: "Approval at the risky steps" },
          { icon: "FaShieldHalved", title: "Guardrails", text: "Keep inputs and outputs safe" },
          { icon: "FaPeopleGroup", title: "Multiple agents", text: "Specialists that collaborate" },
          { icon: "FaEye", title: "Observability", text: "Traces of every step" },
          { icon: "FaGaugeHigh", title: "Evaluation", text: "Measure answer quality" },
        ] },
      ],
    },

    // ---------------------------------------------------------------- setup
    {
      title: "Hands-on Setup",
      subtitle: "Once per laptop – every later session reuses this environment",
      demo: S + "1_5_openai_basic.py",
      left: [
        { type: "steps", items: [
          { title: "Install Python 3.12, VS Code and git" },
          { title: "Fork the course repository", text: "github.com/atulkahatecdac/agenticai → Fork → keep the name agenticai" },
          { title: "Clone it and open it in VS Code", text: "`git clone https://github.com/YOUR-USERNAME/agenticai`" },
          { title: "Create and activate a virtual environment", text: "VS Code: Ctrl+Shift+P → Python: Select Interpreter" },
          { title: "Add your OpenAI API key to .env", text: "platform.openai.com → API keys → copy into `.env`" },
        ] },
      ],
      right: [
        { type: "code", caption: "Terminal", code:
`cd agenticai
python -m venv myenv

# Windows (if blocked, first run:
#   Set-ExecutionPolicy -Scope Process Bypass)
myenv\\Scripts\\activate
# macOS / Linux
source myenv/bin/activate

pip install openai openai-agents python-dotenv

# .env  (in the repo root)
OPENAI_API_KEY=sk-...` },
      ],
    },
    {
      title: "First Call: Talking to an LLM Directly",
      subtitle: "The lowest level – one request, one response, no agent",
      demo: S + "1_5_openai_basic.py",
      split: [1, 1.3],
      left: [
        { type: "icons", items: [
          { icon: "FaKey", title: "API key from .env", text: "`load_dotenv()` puts OPENAI_API_KEY into the environment" },
          { icon: "FaComments", title: "Messages in, text out", text: "A system message sets the role; the user message asks the question" },
          { icon: "FaTriangleExclamation", title: "No tools, no memory, no loop", text: "Everything else an agent does, we would have to code ourselves" },
        ] },
      ],
      right: [
        { type: "code", caption: "1_5_openai_basic.py", code:
`from openai import OpenAI
from dotenv import load_dotenv
load_dotenv(override=True)

client = OpenAI()
response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "system",
         "content": "You are a helpful assistant"},
        {"role": "user",
         "content": "Explain agentic AI in one paragraph"},
    ],
)
print(response.choices[0].message.content)` },
      ],
    },
    {
      title: "SDK, API and Endpoint",
      subtitle: "Who runs where when our agent talks to the model",
      demo: "Concept",
      blocks: [
        { type: "flow", items: [
          { icon: "FaPython", label: "Our code", caption: "Agent logic in Python" },
          { icon: "FaCubes", label: "Agents SDK", caption: "Runs on our machine; builds the requests" },
          { icon: "FaPlug", label: "API endpoint", caption: "HTTPS URL exposed by the provider" },
          { icon: "FaMicrochip", label: "LLM", caption: "GPT model running on OpenAI's servers" },
        ] },
        { type: "table", widths: [1, 1.6, 2.2], head: ["Term", "Full form", "Where it runs"], rows: [
          ["SDK", "Software Development Kit", "On our client – a Python library we import"],
          ["API", "Application Programming Interface", "On the server side – the model provider"],
          ["Endpoint", "The URL of one API operation", "e.g. the chat completions or responses endpoint"],
        ] },
      ],
    },

    // ---------------------------------------------------------------- Agents SDK
    {
      title: "OpenAI Agents SDK",
      subtitle: "pip install openai-agents  ·  define an agent → add tools → run it → inspect the result",
      demo: S + "1_2_openai_agent_basic.py",
      blocks: [
        { type: "cards", size: 10.5, items: [
          { icon: "FaRobot", title: "Agents", lines: ["An LLM with instructions and tools", "**e.g.** a support bot answering FAQs with function calls"] },
          { icon: "FaRightLeft", title: "Handoffs", lines: ["An agent delegates to another agent", "**e.g.** general support hands billing questions to a billing agent"] },
          { icon: "FaShieldHalved", title: "Guardrails", lines: ["Validate inputs and outputs", "**e.g.** block unsafe requests, check the output is valid JSON"] },
          { icon: "FaClockRotateLeft", title: "Sessions", lines: ["Keep conversation history across runs", "**e.g.** a tutor remembers topics already covered"] },
        ] },
        { type: "text", size: 11.5, color: "slate", text: "Also built in: tracing, MCP tools and human approval. The SDK runs the agent loop for us instead of us hand-coding it." },
      ],
    },
    {
      title: "Your First Agent",
      subtitle: "Two objects: Agent describes it, Runner runs it",
      demo: S + "1_2_openai_agent_basic.py",
      split: [1.35, 1],
      left: [
        { type: "code", caption: "1_2_openai_agent_basic.py", code:
`from dotenv import load_dotenv
from agents import Agent, Runner
load_dotenv(override=True)

agent = Agent(
    name="Assistant",
    instructions="You are a helpful customer support analyst.",
    model="gpt-4o-mini",          # optional
)

result = Runner.run_sync(agent,
    "Analyze this customer feedback and suggest improvements: "
    "'The product was a bit stale'")
print(result.final_output)` },
      ],
      right: [
        { type: "icons", d: 0.38, items: [
          { icon: "FaRobot", title: "Agent(...)", text: "Creates, but does not run, the agent: a name, a system prompt (instructions) and a model" },
          { icon: "FaPlay", title: "Runner.run_sync(...)", text: "Sends instructions + message to the LLM and waits for the answer" },
          { icon: "FaReply", title: "result.final_output", text: "The agent's final answer, after any tool calls" },
        ] },
      ],
    },

    // ---------------------------------------------------------------- tools
    { kind: "image", src: "ai_tool_system.png", alt: "AI tool system at a glance", demo: S + "1_6_openai_agent_pattern_tool.py" },
    {
      title: "How a Tool Call Works",
      subtitle: "The LLM decides and describes the call; our code executes it",
      demo: S + "1_6_openai_agent_pattern_tool.py",
      blocks: [
        { type: "flow", items: [
          { icon: "FaUser", label: "User input", caption: "\"What is the return policy?\"" },
          { icon: "FaBrain", label: "Decide", caption: "Answer directly, or call a tool?" },
          { icon: "FaFileCode", label: "Tool call", caption: "Structured call that matches the tool's schema" },
          { icon: "FaGears", label: "Runner executes", caption: "Runs our Python function with those arguments" },
          { icon: "FaReply", label: "Final answer", caption: "LLM combines the tool result into a reply" },
        ] },
        { type: "cards", size: 10.5, items: [
          { title: "LLM (agent)", tag: "Decides", lines: ["Chooses when to call a tool, using its instructions, the context and the tool schemas"] },
          { title: "Tool / function", tag: "Does the work", lines: ["Name, description (docstring) and parameters, plus the code to run"] },
          { title: "Runner", tag: "Connects them", lines: ["Passes the call to our function, handles async and errors, returns the result"] },
        ] },
      ],
    },
    {
      title: "Writing a Tool",
      subtitle: "A normal Python function plus a decorator – the docstring tells the agent when to use it",
      demo: S + "1_6_openai_agent_pattern_tool.py",
      left: [
        { type: "code", caption: "Step 1 – the function", code:
`from agents import function_tool

@function_tool
def get_temperature(city: str) -> str:
    """Returns mock temperature for a city."""
    temps = {"london": "65°F", "tokyo": "78°F",
             "mumbai": "85°F"}
    return temps.get(city.lower(), "70°F")` },
        { type: "code", caption: "Step 2 – give it to the agent", code:
`agent = Agent(
    name="QuickAssistant",
    tools=[get_temperature, get_time, calculate],
    instructions="Use tools when needed. Be concise.",
)` },
      ],
      right: [
        { type: "icons", d: 0.38, items: [
          { icon: "FaTag", title: "@function_tool", text: "Turns the function into a tool and generates its JSON schema from the type hints" },
          { icon: "FaComment", title: "The docstring matters", text: "The agent reads it to decide if and when to call the tool – make it clear and specific" },
          { icon: "FaListCheck", title: "Type hints are the contract", text: "`city: str` becomes a required string parameter the LLM must fill in" },
        ] },
      ],
    },
    { kind: "image", src: "building_an_ai_agent.png", alt: "Building an AI agent in seven steps", demo: S + "1_1_my_first_agent.py" },
    {
      title: "A Multi-Tool Agent, End to End",
      subtitle: "Three tools, one agent, three questions answered concurrently",
      demo: S + "1_1_my_first_agent.py",
      split: [1.3, 1],
      left: [
        { type: "code", caption: "1_1_my_first_agent.py (condensed)", code:
`@function_tool
def get_temperature(city: str) -> str: ...
@function_tool
def get_time(timezone: str) -> str: ...
@function_tool
def calculate(expression: str) -> str: ...

agent = Agent(name="QuickAssistant", model="gpt-4o-mini",
    tools=[get_temperature, get_time, calculate],
    instructions="Use tools when needed. Be concise.")

async def run_agent():
    queries = ["What's the temperature in Tokyo?",
               "Calculate 25 * 4 + 10",
               "What time is it in New York?"]
    tasks = [Runner.run(agent, q) for q in queries]
    results = await asyncio.gather(*tasks)
    for q, r in zip(queries, results):
        print(f"Q: {q}\\nA: {r.final_output}")` },
      ],
      right: [
        { type: "table", size: 10, widths: [1.25, 2], head: ["Code", "What it does"], rows: [
          ["`@function_tool`", "Makes each function callable by the agent"],
          ["`tools=[...]`", "The menu of tools the agent may choose from"],
          ["`queries`", "Plain-language questions – the agent picks the tool"],
          ["`Runner.run(...)`", "Async run; the list holds one task per query"],
          ["`asyncio.gather`", "Runs all tasks at once, waits for all"],
          ["`final_output`", "Each agent's answer after its tool calls"],
        ] },
      ],
    },

    // ---------------------------------------------------------------- sync / async
    {
      title: "Sync or Async?",
      subtitle: "Same agent, two ways to run it",
      demo: S + "1_7_openai_agent_sync.py, 1_8_openai_agent_async.py",
      blocks: [
        { type: "compare", size: 11, cols: [
          { title: "Synchronous – Runner.run_sync(...)", color: "navy", items: [
            "Blocking: one call at a time, each waits for the previous",
            "Simple to write – no async / await",
            "Best for scripts, one-off calls, debugging",
            "Slower when there are many requests",
          ], code: `result = Runner.run_sync(agent, msg)
print(result.final_output)` },
          { title: "Asynchronous – await Runner.run(...)", color: "teal", items: [
            "Non-blocking: many LLM or tool calls in parallel",
            "Needs asyncio and await",
            "Best for production apps, web servers, many sessions",
            "Higher throughput; errors via gather, timeouts, cancellation",
          ], code: `async def main():
    result = await Runner.run(agent, msg)
asyncio.run(main())` },
        ] },
      ],
    },
    { kind: "image", src: "sync_vs_async_timing.png", alt: "Sync vs async: total time 15 s vs 6 s", demo: S + "1_7_openai_agent_sync.py, 1_8_openai_agent_async.py" },

    // ---------------------------------------------------------------- patterns
    { kind: "image", src: "four_agentic_patterns.png", alt: "Four agentic AI patterns at a glance", demo: S + "1_9_openai_agent_pattern_plan.py, 1_4_…_react.py, 1_10_…_reflection.py, 1_3_…_rewoo.py" },
    {
      title: "Pattern: Tool Use",
      subtitle: "The agent decides when and how to call external tools instead of doing everything itself",
      demo: S + "1_6_openai_agent_pattern_tool.py",
      blocks: [
        { type: "flow", items: [
          { icon: "FaMagnifyingGlass", label: "Analyse", caption: "Understand the task" },
          { icon: "FaScrewdriverWrench", label: "Choose", caption: "Pick a suitable tool" },
          { icon: "FaPaperPlane", label: "Call", caption: "Send structured input" },
          { icon: "FaInbox", label: "Receive", caption: "Get the tool's output" },
          { icon: "FaPuzzlePiece", label: "Integrate", caption: "Fold it into the answer" },
        ] },
        { type: "tiles", cols: 4, items: [
          { icon: "FaCubes", title: "Modular", text: "Each tool is a specialist" },
          { icon: "FaUpRightAndDownLeftFromCenter", title: "Scalable", text: "Add tools, not code paths" },
          { icon: "FaListCheck", title: "Auditable", text: "Clear trace of who did what" },
          { icon: "FaGaugeHigh", title: "Efficient", text: "Offload work to optimised tools" },
        ] },
      ],
    },
    {
      title: "Pattern: ReAct (Reason + Act)",
      subtitle: "Think, act, look at the result, think again – until the goal is reached",
      demo: S + "1_4_openai_agent_pattern_react.py",
      blocks: [
        { type: "flow", loop: "repeat until the goal is achieved", items: [
          { icon: "FaBrain", label: "Thought", caption: "What do I need next?" },
          { icon: "FaScrewdriverWrench", label: "Action", caption: "Call the right tool" },
          { icon: "FaEye", label: "Observation", caption: "Read the tool's result" },
          { icon: "FaCircleCheck", label: "Answer", caption: "Stop when the goal is met" },
        ] },
        { type: "callout", eyebrow: "Why it works", text: "The next step is chosen from the latest observation, so the agent adapts as it learns more – ideal when the path to the answer is not known up front." },
      ],
    },
    {
      title: "Pattern: Plan-and-Execute",
      subtitle: "Plan the whole job first, then carry out the steps",
      demo: S + "1_9_openai_agent_pattern_plan.py",
      blocks: [
        { type: "chain", items: ["Goal", "Planner", "Execution plan", "Executor", "Step 1", "Step 2", "Step 3", "Final answer"], highlight: [1, 3] },
        { type: "cards", size: 11, items: [
          { icon: "FaListOl", title: "Planning", lines: ["Create a complete plan to reach the goal before doing anything"] },
          { icon: "FaPersonRunning", title: "Execution", lines: ["Carry out each step in order; each step can be a small ReAct loop of its own"] },
          { icon: "FaScaleBalanced", title: "vs ReAct", lines: ["ReAct decides after every observation; plan-and-execute commits to a strategy first"] },
        ] },
      ],
    },
    {
      title: "Pattern: Multi-Agent",
      subtitle: "Specialised agents collaborate on one problem, coordinated by an orchestrator",
      demo: S + "1_11_openai_agent_pattern_multi_agent.py",
      blocks: [
        { type: "flow", items: [
          { icon: "FaUser", label: "Request", caption: "Arrives at the orchestrator" },
          { icon: "FaSitemap", label: "Decompose", caption: "Split into sub-tasks" },
          { icon: "FaPeopleGroup", label: "Assign", caption: "Each sub-task to a specialist" },
          { icon: "FaGears", label: "Execute", caption: "In parallel or in sequence" },
          { icon: "FaLayerGroup", label: "Aggregate", caption: "Combine and validate" },
        ] },
        { type: "tiles", cols: 4, items: [
          { icon: "FaUserTie", title: "Specialisation", text: "Each agent does one thing well" },
          { icon: "FaUpRightAndDownLeftFromCenter", title: "Scalability", text: "Add or swap agents freely" },
          { icon: "FaBolt", title: "Parallelism", text: "Agents work concurrently" },
          { icon: "FaShieldHalved", title: "Robustness", text: "One failure doesn't sink the rest" },
        ] },
      ],
    },
    {
      title: "From FAQ Bot to RAG: The Code Ladder",
      subtitle: "Each script adds one capability to the previous one",
      demo: S + "1_12_* … 1_23_*",
      blocks: [
        { type: "table", size: 9.5, widths: [0.35, 2.4, 2.2, 2.4], head: ["#", "What changes", "Pattern / feature", "Script"], rows: [
          ["1", "FAQ bot with a hardcoded knowledge base, keyword match", "Function calling", "1_12_openai_agent_tool_hardcoded_knowledge.py"],
          ["2", "Search by meaning instead of keywords", "Semantic search (embeddings)", "1_13_openai_agent_hardcoded_semantic.py"],
          ["3", "Let OpenAI host the vector store", "Hosted RAG", "1_14_openai_agent_openai_vectorstore.py"],
          ["4", "FAQs in SQLite, vectorised locally", "Basic RAG", "1_15_…_create_faq_db.py → 1_16_…_faq_db_vectorized.py"],
          ["5", "Chat UI in the browser", "Separate the UI (Flask)", "1_17_openai_agent_flask.py"],
          ["6", "Answers from an insurance PDF", "RAG over a document", "1_18_openai_agent_insurance_flask.py"],
          ["7", "Block unsafe or off-topic input", "Guardrails", "1_19_openai_agent_guardrails.py"],
          ["8", "Traditional vs agentic RAG", "Agentic RAG", "1_20_… vs 1_21_…_agentic_rag.py"],
          ["9", "Agents used as tools by a manager agent", "Agents as tools", "1_22_openai_agent_agent_as_tool.py"],
          ["10", "Remember earlier turns", "Short-term memory", "1_23_openai_agent_short_term_memory.py"],
        ] },
      ],
    },
    {
      title: "The Agentic AI Framework Landscape",
      subtitle: "From raw API calls to full multi-agent frameworks – the order we cover them in",
      demo: "Concept",
      blocks: [
        { type: "table", size: 10, widths: [0.4, 1.6, 1.9, 4.1], head: ["", "Tool / framework", "Role", "Why it fits here"], rows: [
          ["1", "OpenAI SDK", "Base API / SDK", "Lowest level – call LLMs and embeddings; everything else builds on it"],
          ["2", "OpenAI Agents SDK", "Structured agents", "Adds agents, tools, handoffs, guardrails and sessions"],
          ["3", "LangChain / LangGraph", "Chains and agent graphs", "Compose workflows as graphs: predictable flows, loops, multi-agent"],
          ["4", "CrewAI", "Multi-agent crews", "Role-based agents collaborating on tasks; built for autonomy"],
          ["5", "AutoGen", "Conversational multi-agent", "Agents that talk to each other: debate, negotiate, review"],
          ["6", "MCP", "Protocol", "Standard agent ↔ tool connection that makes all of the above interoperable"],
          ["7", "No-code / low-code", "Visual builders", "Drag-and-drop agents with many connectors (n8n, OpenAI Agent Builder)"],
        ] },
      ],
    },

    {
      kind: "summary",
      title: "Session 1 Summary",
      subtitle: "What you built today",
      built: [
        { tag: "1_2", title: "A first agent", text: "Agent + Runner.run_sync, with instructions and a model" },
        { tag: "1_6", title: "Tools", text: "@function_tool functions the agent decides to call" },
        { tag: "1_1", title: "Multi-tool async agent", text: "Three tools, three queries, run concurrently with asyncio.gather" },
        { tag: "1_4", title: "Design patterns", text: "ReAct, plan-and-execute, reflection, ReWOO, multi-agent" },
        { tag: "1_12+", title: "FAQ bot → RAG ladder", text: "Semantic search, vector stores, guardrails, memory" },
      ],
      takeaways: [
        "An agent = LLM + instructions + tools + a loop",
        "The LLM only describes a tool call – our code runs it",
        "Docstrings and type hints are how the agent understands a tool",
        "Use async when calls are independent; sync when each step needs the last",
        "Pick a pattern by how predictable the path to the answer is",
      ],
      next: "Session 2: LangChain Core – Chains, Memory and RAG",
    },
  ],
};
