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
        { icon: "FaDiagramProject", title: "Build graphs from state, nodes and edges", text: "TypedDict state, StateGraph, compile and invoke" },
        { icon: "FaCodeMerge", title: "Merge updates with reducers", text: "so parallel nodes don't overwrite each other" },
        { icon: "FaRoute", title: "Route, stream and debug", text: "conditional edges, message graphs, streaming, LangGraph Studio" },
      ],
      agenda: [
        "Why LangGraph (LangChain vs LangGraph)",
        "Core components: state, nodes, edges",
        "Building the first graph",
        "Reducers",
        "Conditional routing",
        "Message graphs",
        "Streaming",
        "Multi-node pipelines and LangGraph Studio",
      ],
    },
    {
      title: "Three Ways to Work with LLMs",
      subtitle: "The same \"summarise this text\" task – with plain Python, a LangChain chain, and a LangGraph graph",
      demo: S + "4_1_not_langgraph_langchain_instead.py",
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
      demo: S + "4_1_not_langgraph_langchain_instead.py",
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
      subtitle: "A bank-transfer graph: check the balance, then buy or sell, then update the balance",
      demo: S + "4_2_greeter_graph.py",
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
        { type: "tree", boxW: 2.2, rows: [["START"], [{ label: "transaction_node", fill: "navy" }], ["buy_node", "sell_node"], [{ label: "balance_node", fill: "navy" }], ["END"]] },
      ],
    },
    {
      title: "Shared State with TypedDict",
      subtitle: "Nodes don't pass many variables to each other – they read and update one shared state",
      demo: S + "4_2_greeter_graph.py",
      split: [1, 1.35],
      left: [
        { type: "code", caption: "Every node now knows which fields exist", code:
`class BankState(TypedDict):
    customer_id: str
    balance: float
    transfer_amount: float
    transaction_id: str` },
        { type: "callout", eyebrow: "Partial updates", text: "A node returns only the fields it changed; LangGraph merges them into the full state." },
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
      demo: S + "4_3_langgraph_basic.py",
      split: [1.3, 1],
      left: [
        { type: "code", caption: "4_3_langgraph_basic.py (condensed)", code:
`class GraphState(TypedDict):
    user_name: str
    greeting: str

def ask_name_node(state):
    name = input("Bot: What is your name? ")
    return {**state, "user_name": name}

def greet_user_node(state):
    return {**state,
            "greeting": f"Hello {state['user_name']}!"}

workflow = StateGraph(GraphState)
workflow.add_node("ask_name", ask_name_node)
workflow.add_node("greet_user", greet_user_node)
workflow.add_edge(START, "ask_name")
workflow.add_edge("ask_name", "greet_user")
workflow.add_edge("greet_user", END)
app = workflow.compile()
app.invoke({"user_name": "", "greeting": ""})` },
      ],
      right: [
        { type: "chain", size: 10, items: ["START", "ask_name", "greet_user", "END"], highlight: [1, 2] },
        { type: "icons", d: 0.34, size: 10.5, titleSize: 12, gap: 0.12, items: [
          { icon: "FaDatabase", title: "State", text: "A shared clipboard every node reads and writes" },
          { icon: "FaCircleDot", title: "Nodes", text: "Plain functions: state in, updated state out (`**state` keeps the rest)" },
          { icon: "FaArrowRight", title: "Edges", text: "START → ask_name → greet_user → END" },
          { icon: "FaPlay", title: "compile() and invoke()", text: "Build the runnable graph, then run it from an initial state" },
        ] },
      ],
    },
    {
      title: "Reducers: Merging Updates to the Same Key",
      subtitle: "When several nodes write the same field, the reducer decides how values combine",
      demo: S + "4_4_…_without_reducer.py, 4_5_…_with_reducer.py, 4_6_langgraph_reducer_return_policy.py",
      blocks: [
        { type: "compare", size: 11, codeSize: 9, cols: [
          { title: "Without a reducer – last write wins", color: "slate", items: ["Agent B's message replaces Agent A's"], code:
`class State(TypedDict):
    messages: List[str]

def agent_a(state):
    return {"messages": ["Hello from A"]}
def agent_b(state):
    return {"messages": ["Hello from B"]}` },
          { title: "With a reducer – values accumulate", color: "teal", items: ["Both messages are kept, in order"], code:
`def add_messages(old, new):
    return old + new        # the reducer

class State(TypedDict):
    messages: Annotated[List[str], add_messages]
# agent_a and agent_b unchanged – nothing is lost` },
        ] },
        { type: "text", size: 11.5, color: "slate", text: "**With an LLM (4_6):** two agents check the return policies of two e-commerce sites in parallel; a reducer combines their findings." },
      ],
    },
    {
      title: "Conditional Edges: Choosing the Next Node",
      subtitle: "Follow a path based on the current state instead of one fixed route",
      demo: S + "4_7_…_routing_specialists.py, 4_10_stock_price_graph.py, 4_11_…_sentiment_graph.py",
      blocks: [
        { type: "flow", items: [
          { icon: "FaCircleDot", label: "Node", caption: "Updates the state" },
          { icon: "FaCodeBranch", label: "Routing function", caption: "Reads the state and returns a label", color: "coral" },
          { icon: "FaRoute", label: "Mapped node", caption: "The edge for that label is followed", color: "teal" },
        ] },
        { type: "tiles", cols: 3, items: [
          { icon: "FaFileSignature", title: "Loan approved or rejected?", text: "Different follow-up nodes" },
          { icon: "FaWallet", title: "Enough balance?", text: "Transfer or decline" },
          { icon: "FaUserLock", title: "Customer authenticated?", text: "Continue or ask again" },
        ] },
        { type: "text", size: 11, color: "slate", text: "Compare `4_10` (unconditional edges) with `4_11` (conditional on news sentiment); `4_7` routes questions to specialist nodes." },
      ],
    },
    {
      title: "Message Graphs",
      subtitle: "When the conversation itself is the state",
      demo: S + "4_8_message_graph_bank_faq.py",
      split: [1, 1],
      left: [
        { type: "text", text: "Instead of separate fields such as question, answer and context, the state is a list of **messages**. Each node reads the history and appends to it." },
        { type: "callout", eyebrow: "Key idea", text: "The conversation becomes the state of the graph – ideal for chat assistants like the bank FAQ demo." },
      ],
      right: [
        { type: "code", caption: "State", code:
`state
└── messages
    ├── SystemMessage
    ├── HumanMessage
    ├── AIMessage
    ├── HumanMessage
    └── AIMessage` },
      ],
    },
    {
      title: "Streaming and LangGraph Studio",
      subtitle: "See progress while the graph runs, and see the graph itself while you build it",
      demo: S + "4_9_streaming_stock_recommendation.py, langgraph.json, 4_10_…_graph.py, 4_11_…_graph.py",
      blocks: [
        { type: "cols", cols: [
          [
            { type: "text", text: "**Streaming**", size: 13 },
            { type: "bullets", size: 11.5, items: [
              "Normally the graph runs every node, then returns",
              "With streaming, each node's output is sent as soon as it completes",
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
    { kind: "image", src: "langgraph_memory_options.png", alt: "LangGraph memory options: no memory, MemorySaver, SqliteSaver", demo: S + "4_12_langgraph_news_summarizer.py; session_5/5_7_langgraph_memory.py" },
    {
      title: "More LangGraph Examples",
      subtitle: "Bigger demos that combine everything so far – several continue into Session 5",
      demo: S + "4_12_…_news_summarizer.py (+4_13/4_14), 4_15_…_sector_outlook.py, 4_16_…_planner_agent.py",
      blocks: [
        { type: "table", size: 10, widths: [2.2, 3.3, 2.6], head: ["Example", "What it shows", "Code"], rows: [
          ["News summariser", "External API + conditional logic on news sentiment", "4_12 (4_13 Ollama, 4_14 Gemini)"],
          ["Company sector outlook", "Multi-node research pipeline", "4_15"],
          ["Code security reviewer", "Workflow version vs a planner agent that decides", "session_5/5_2, 4_16"],
          ["Bank chatbot (real data)", "Kaggle FAQs in ChromaDB, Flask UI", "session_5/5_15"],
          ["Notifications", "ntfy.sh push messages and Gmail", "session_5/5_16"],
          ["Guardrails", "Build from a Hugging Face dataset, test, apply to the bank bot", "session_5/5_12 → 5_14"],
          ["Short-term memory + RAG", "Answer from memory first, else the vector DB", "session_5/5_17"],
        ] },
      ],
    },
    {
      title: "Setup: Sending Email from Code",
      subtitle: "The notification demos send mail through Gmail with an app password",
      demo: "session_5/5_16_langgraph_bank_ntfy_email_flask.py",
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
        { tag: "4_1", title: "Same task, three ways", text: "Plain Python vs LangChain vs LangGraph" },
        { tag: "4_3", title: "First graph", text: "State, two nodes, edges, compile and invoke" },
        { tag: "4_5", title: "Reducers", text: "Parallel agents adding to the same list" },
        { tag: "4_7", title: "Conditional routing", text: "Routing functions that pick the next node" },
        { tag: "4_12", title: "News summariser", text: "An API-driven graph with sentiment-based branches" },
      ],
      takeaways: [
        "Use LangGraph when you need state, branches or loops",
        "State is the contract between nodes – design it first",
        "Nodes return partial updates; reducers decide how they merge",
        "Conditional edges turn a pipeline into a decision-maker",
        "Stream for responsiveness; use Studio to see and debug the graph",
      ],
      next: "Session 5: LangGraph – Cycles, Human-in-the-Loop and Persistence",
    },
  ],
};
