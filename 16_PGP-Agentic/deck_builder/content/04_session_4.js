const S = "session_4/";

module.exports = {
  section: "Session 4 – LangGraph Workflows",
  slides: [
    {
      kind: "opener",
      eyebrow: "Session 4  ·  Sat 1-Nov  ·  08:00–11:00 AM",
      title: "LangGraph: Stateful Workflows and Routing",
      subtitle: "Model an LLM application as a graph: shared state, nodes that update it, and edges that decide what runs next",
      goals: [
        { icon: "FaCodeCompare", title: "Know when to reach for LangGraph", text: "and how it differs from plain LangChain chains" },
        { icon: "FaDiagramProject", title: "Build graphs from state, nodes and edges", text: "TypedDict state, StateGraph, conditional edges" },
        { icon: "FaRoute", title: "Stream and debug", text: "streaming output and LangGraph Studio" },
      ],
      agenda: [
        "Why LangGraph (LangChain vs LangGraph)",
        "Core components: state, nodes, edges",
        "Building the first graph",
        "Conditional edges",
        "Streaming",
        "Multi-node pipelines and LangGraph Studio",
      ],
    },
    {
      title: "Three Ways to Work with LLMs",
      subtitle: "More structure at each level: plain Python, a LangChain chain, and a LangGraph graph",
      demo: "Concept",
      blocks: [
        { type: "cards", size: 10.5, items: [
          { icon: "FaCode", title: "Plain Python (OOP)", tag: "Low abstraction", lines: ["Direct API calls; we write the flow, state and error handling ourselves", "**Fits:** one-off calls, prototypes"] },
          { icon: "FaLink", title: "LangChain (LCEL)", tag: "Medium abstraction", lines: ["A declarative pipeline: prompt → LLM → parser → tool", "Mostly linear; built-in retries and fallbacks", "**Fits:** standard pipelines"] },
          { icon: "FaDiagramProject", title: "LangGraph", tag: "High abstraction", lines: ["Nodes and edges over an explicit, persistent state", "Branches, loops, parallel paths, conditional routing", "**Fits:** stateful, multi-step, multi-agent work"] },
        ] },
      ],
    },
    {
      title: "LangChain vs LangGraph",
      subtitle: "LangGraph builds on LangChain; it doesn't replace it",
      demo: "Concept",
      blocks: [
        { type: "table", size: 10.5, widths: [1.5, 3, 3], head: ["Aspect", "LangChain", "LangGraph"], rows: [
          ["Purpose", "Use LLMs with tools, retrievers and parsers", "Complex, stateful, multi-agent applications"],
          ["Workflow", "Simple, single-step or short chains", "Multi-step, long-running, with loops"],
          ["State", "Minimal; memory handled outside", "Built-in shared state across every step"],
          ["Control flow", "Mostly predefined steps", "Dynamic branching and runtime decisions"],
          ["Best for", "Chatbots, document Q&A, calculators", "Automation, multi-agent orchestration"],
          ["Learning curve", "Easier", "Steeper: state, nodes, edges, coordination"],
        ] },
      ],
    },
    {
      title: "LangGraph: Four Key Components",
      subtitle: "A simple greeting graph: ask for a name, then greet the user",
      demo: S + "4_1_langgraph_basic.py",
      split: [1.25, 1],
      left: [
        { type: "icons", d: 0.4, items: [
          { icon: "FaDatabase", title: "State", text: "The data that flows through the graph and is updated at each step" },
          { icon: "FaCircleDot", title: "Node", text: "One step: takes the current state, returns an updated state" },
          { icon: "FaArrowRight", title: "Edge", text: "Connects two nodes and decides how control flows between them" },
          { icon: "FaDiagramProject", title: "Graph", text: "The overall structure that organises nodes and edges" },
        ] },
      ],
      right: [
        { type: "tree", boxW: 2.2, rows: [["START"], [{ label: "step_1 (ask_name)", fill: "navy" }], [{ label: "step_2 (greet_user)", fill: "navy" }], ["END"]] },
      ],
    },
    {
      title: "Shared State with TypedDict",
      subtitle: "Nodes don't pass many variables to each other – they read and update one shared state",
      demo: S + "4_1_langgraph_basic.py, 4_2_greeter_graph.py",
      split: [1, 1.35],
      left: [
        { type: "code", caption: "Every node now knows which fields exist", code:
`class InputState(TypedDict):
    name: str
    greeting: str` },
        { type: "callout", eyebrow: "Partial updates", text: "A node can return only the fields it changed: classify_mood in 4_2 returns just {\"mood\": ...}, and LangGraph merges it in." },
      ],
      right: [
        { type: "table", size: 10, widths: [1.3, 1.7, 1.9], head: ["", "TypedDict", "Pydantic BaseModel"], rows: [
          ["Purpose", "Type hints for dicts", "Validation and parsing"],
          ["At runtime", "Not enforced", "Enforced, with type conversion"],
          ["Defaults", "Not supported", "Supported"],
          ["Nested models", "Plain nested dicts", "Fully supported"],
          ["Speed", "Faster – no checks", "Slower – validates"],
          ["Use when", "You just need structure", "You need validation (e.g. API input)"],
        ] },
      ],
    },
    {
      title: "Your First Graph",
      subtitle: "Ask for a name, then greet the user – two nodes over a shared state",
      demo: S + "4_1_langgraph_basic.py",
      split: [1.3, 1],
      left: [
        { type: "code", caption: "4_1_langgraph_basic.py (condensed)", code:
`class InputState(TypedDict):
    name: str
    greeting: str

def ask_name(state):
    user_name = input("Bot: What's your name? ")
    return {"name": user_name, "greeting": ""}

def greet_user(state):
    name = state.get("name") or "there"
    greeting = f"Hello {name}, nice to meet you!"
    return {"name": name, "greeting": greeting}
graph = StateGraph(InputState)
graph.add_node("step_1", ask_name)
graph.add_node("step_2", greet_user)
graph.add_edge(START, "step_1")
graph.add_edge("step_1", "step_2")
graph.add_edge("step_2", END)
app = graph.compile()
app.invoke({"name": "", "greeting": ""})` },
      ],
      right: [
        { type: "chain", size: 10, items: ["START", "step_1", "step_2", "END"], highlight: [1, 2] },
        { type: "icons", d: 0.34, size: 10.5, titleSize: 12, gap: 0.12, items: [
          { icon: "FaDatabase", title: "State", text: "A shared clipboard every node reads and writes" },
          { icon: "FaCircleDot", title: "Nodes", text: "Plain functions: state in, updated fields out" },
          { icon: "FaArrowRight", title: "Edges", text: "START → step_1 → step_2 → END" },
          { icon: "FaPlay", title: "compile() and invoke()", text: "Build the runnable graph, then run it from an initial state" },
        ] },
      ],
    },
    {
      title: "Conditional Edges: Choosing the Next Node",
      subtitle: "A plain edge always goes to the same node; a conditional edge picks one from the current state",
      demo: S + "4_2_greeter_graph.py, 4_4_stock_price_graph.py, 4_5_stock_news_sentiment_graph.py",
      split: [1.25, 1],
      left: [
        { type: "code", caption: "From 4_2_greeter_graph.py", code:
`def route_by_mood(state):
    return state["mood"]    # "happy" or "sad"

graph.add_conditional_edges(
    "classify_mood",        # after this node
    route_by_mood,          # call this function
    {"happy": "cheerful_reply",     # label -> next node
     "sad": "sympathetic_reply"},
)` },
        { type: "text", size: 11, color: "slate", text: "`4_4` uses only plain edges. `4_5` adds one conditional edge: positive news goes to `invest_summary`, negative to `alternatives_summary`." },
      ],
      right: [
        { type: "tree", boxW: 2.2, rows: [["START"], [{ label: "classify_mood", fill: "navy" }], ["cheerful_reply", "sympathetic_reply"], ["END"]] },
      ],
    },
    {
      title: "Streaming and LangGraph Studio",
      subtitle: "See progress while the graph runs, and see the graph itself while you build it",
      demo: S + "4_3_streaming_stock_recommendation.py, langgraph.json, 4_5_stock_news_sentiment_graph.py",
      blocks: [
        { type: "cols", cols: [
          [
            { type: "text", text: "**Streaming**", size: 13 },
            { type: "bullets", size: 11.5, items: [
              "Normally the graph runs every node, then returns",
              "`stream_mode=\"updates\"`: each node's output as soon as it completes",
              "`stream_mode=\"messages\"`: the LLM's answer token by token",
              "Users see progress instead of waiting",
            ] },
          ],
          [
            { type: "text", text: "**LangGraph Studio** – a visual IDE for graphs", size: 13 },
            { type: "code", code:
`uv pip install "langgraph-cli[inmem]"
langgraph dev --tunnel     # opens Studio
# "domain not allowed"? Advanced settings →
#   Allowed domains: *.trycloudflare.com
# pick stock_news, input: hdfcbank
# Ctrl+C to stop` },
          ],
        ] },
      ],
    },
    { kind: "image", src: "langgraph_memory_options.png", alt: "LangGraph memory options: no memory, MemorySaver, SqliteSaver", demo: "session_5/5_4_langgraph_memory.py (covered in Session 5)" },
    {
      title: "More LangGraph Examples",
      subtitle: "Bigger demos that combine everything so far – several continue into Session 5",
      demo: S + "4_6_…_news_summarizer.py (+4_7/4_8), 4_9_…_sector_outlook.py, 4_10_…_planner_agent.py",
      blocks: [
        { type: "table", size: 10, widths: [2.2, 3.3, 2.6], head: ["Example", "What it shows", "Code"], rows: [
          ["News summariser", "External API + conditional logic on news sentiment", "4_6 (4_7 Ollama, 4_8 Gemini)"],
          ["Company sector outlook", "Multi-node research pipeline", "4_9"],
          ["Code security reviewer", "A planner agent decides the review steps", "4_10"],
          ["Bank chatbot (real data)", "Kaggle FAQs in ChromaDB, ntfy.sh and Gmail, Flask UI", "session_5/5_7"],
          ["Guardrails", "Build from a Hugging Face dataset, apply to the bank bot", "session_5/5_8 → 5_9"],
          ["Short-term memory + RAG", "Answer from memory first, else the vector DB", "session_5/5_10"],
        ] },
      ],
    },
    {
      title: "Setup: Sending Email from Code",
      subtitle: "The notification demos send mail through Gmail with an app password",
      demo: "session_5/5_7_langgraph_bank_ntfy_email_flask.py",
      blocks: [
        { type: "steps", items: [
          { title: "Open your Google Account", text: "Security and sign-in" },
          { title: "Turn on 2-step verification", text: "App passwords are only available with it enabled" },
          { title: "Create an app password", text: "Use the \"App passwords\" option, or go to myaccount.google.com/apppasswords" },
          { title: "Put it in .env", text: "Copy the 16-character password without spaces into `GMAIL_APP_PASSWORD`" },
        ] },
      ],
    },
    {
      kind: "summary",
      title: "Session 4 Summary",
      subtitle: "What you built today",
      built: [
        { tag: "4_1", title: "First graph", text: "State, two nodes, edges, compile and invoke" },
        { tag: "4_2", title: "Mood greeter", text: "State, nodes and a conditional edge" },
        { tag: "4_3", title: "Streaming", text: "Node by node, and token by token" },
        { tag: "4_5", title: "LangGraph Studio", text: "See and debug the stock news graph" },
        { tag: "4_6", title: "News summariser", text: "An API-driven graph with sentiment-based branches" },
      ],
      takeaways: [
        "Use LangGraph when you need state, branches or loops",
        "State is the contract between nodes – design it first",
        "Nodes return partial updates; LangGraph merges them into the state",
        "Conditional edges let the state choose the next node",
        "Stream for responsiveness; use Studio to see and debug the graph",
      ],
      next: "Session 5: LangGraph – Cycles, Human-in-the-Loop and Persistence",
    },
  ],
};
