const M = "07_langgraph/";

module.exports = {
  section: "Module 07 – LangGraph",
  slides: [
    {
      kind: "opener",
      eyebrow: "Module 07",
      title: "LangGraph",
      subtitle: "Model an LLM application as a graph: shared state, nodes that update it, and edges that decide what runs next",
      goals: [
        { icon: "FaCodeCompare", title: "Know when to reach for LangGraph", text: "and how it differs from plain LangChain chains" },
        { icon: "FaDiagramProject", title: "Build graphs from state, nodes, edges", text: "TypedDict state, StateGraph, compile and invoke" },
        { icon: "FaRoute", title: "Route with conditional edges", text: "the graph picks its own path from the state" },
        { icon: "FaBug", title: "Stream and debug", text: "message graphs, streaming, LangGraph Studio" },
      ],
      agenda: [
        "Why LangGraph",
        "Core components: state, nodes, edges",
        "State with TypedDict",
        "Building a graph",
        "Conditional edges",
        "Message graphs",
        "Streaming",
        "LangGraph Studio",
      ],
    },
    {
      title: "Why LangGraph?",
      subtitle: "LangChain is good for simple agents; LangGraph uses graphs, not chains – and builds on LangChain",
      demo: "Concept",
      blocks: [
        { type: "table", size: 10.5, widths: [1.5, 3, 3], head: ["Aspect", "LangChain", "LangGraph"], rows: [
          ["Purpose", "Use LLMs with tools, retrievers and parsers", "Complex, stateful, multi-agent applications"],
          ["Workflow", "Simple, single-step or short chains", "Multi-step, long-running, with loops"],
          ["State", "Minimal; memory handled outside", "Built-in shared state across every step"],
          ["Control flow", "Mostly predefined steps", "Conditions, loops, parallel branches"],
          ["Reliability", "Little error recovery", "Retries, human approval, checkpoints"],
          ["Best for", "Chatbots, document Q&A", "Automation, multi-agent orchestration"],
        ] },
      ],
    },
    {
      title: "Core Components: State, Node, Edge",
      subtitle: "\"What is the price of INFY today?\" – flowing through a small graph",
      demo: "Concept",
      split: [1.25, 1],
      left: [
        { type: "icons", d: 0.4, items: [
          { icon: "FaDatabase", title: "State", text: "Shared global memory of the graph – every node receives it and updates it. Starts as `{question, answer: []}`, ends with the answer filled in" },
          { icon: "FaCircleDot", title: "Node", text: "A Python function doing one task – call an LLM, run a tool, query a DB, validate input. State in → updated state out" },
          { icon: "FaArrowRight", title: "Edge", text: "Connects nodes: search → summarise. A conditional edge chooses: enough results? summarise : search again" },
        ] },
      ],
      right: [
        { type: "tree", boxW: 2.0, labels: ["", "enough results?"], rows: [["START"], [{ label: "search", fill: "navy" }], [{ label: "Yes → summarise", fill: "teal" }, "No → search again"], ["END"]] },
      ],
    },
    {
      title: "Shared State with TypedDict",
      subtitle: "Nodes don't pass many variables to each other – they read and update one shared state",
      demo: "Concept",
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
      title: "Building a Graph",
      subtitle: "StateGraph is the blueprint: add nodes, connect edges, compile, invoke",
      demo: M + "greeter_graph.py",
      split: [1.3, 1],
      left: [
        { type: "code", caption: "greeter_graph.py (condensed)", code:
`class GreeterState(TypedDict):
    message: str
    mood: str
    reply: str

def classify_mood(state):      # LLM: happy or sad?
    return {"mood": classify_chain.invoke(...).mood}

graph = StateGraph(GreeterState)
graph.add_node("classify_mood", classify_mood)
graph.add_node("cheerful_reply", cheerful_reply)
graph.add_node("sympathetic_reply", sympathetic_reply)
graph.add_edge(START, "classify_mood")
graph.add_conditional_edges("classify_mood", route_by_mood,
    {"happy": "cheerful_reply", "sad": "sympathetic_reply"})
graph.add_edge("cheerful_reply", END)
graph.add_edge("sympathetic_reply", END)
app = graph.compile()` },
      ],
      right: [
        { type: "tree", boxW: 1.6, size: 10.5, rows: [["START"], [{ label: "classify_mood", fill: "navy" }], ["cheerful_reply", "sympathetic_reply"], ["END"]] },
        { type: "text", size: 11, color: "slate", text: "The simplest graph with a branch – the one LangGraph Studio opens. `app.invoke({\"message\": \"…\"})` runs it." },
      ],
    },
    {
      title: "Conditional Edges: Choosing the Next Node",
      subtitle: "Follow a path based on the current state instead of one fixed route",
      demo: M + "stock_news_sentiment_graph.py, conditional_routing_specialists.py",
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
        { type: "text", size: 11, color: "slate", text: "Compare `stock_price_graph.py` (unconditional edges) with `stock_news_sentiment_graph.py` (branches on news sentiment); `conditional_routing_specialists.py` routes questions to specialist nodes." },
      ],
    },
    {
      title: "A Conditional Graph: Stock News Sentiment",
      subtitle: "Fetch the news, classify its sentiment, then write a different summary for each outcome",
      demo: M + "stock_news_sentiment_graph.py",
      split: [1, 1.1],
      left: [
        { type: "tree", boxW: 1.75, size: 10.5, labels: ["", "", "negative · positive"], rows: [["normalize_symbol"], ["fetch_news"], [{ label: "classify_sentiment", fill: "coral" }], ["alternatives_summary", "invest_summary"]] },
      ],
      right: [
        { type: "steps", size: 10.5, items: [
          { title: "normalize_symbol", text: "\"hdfcbank\" → a proper ticker" },
          { title: "fetch_news", text: "Recent headlines for that company" },
          { title: "classify_sentiment", text: "An LLM labels the news; the routing function reads the label" },
          { title: "Two endings", text: "Negative → suggest alternatives. Positive → an investment summary" },
        ] },
      ],
    },
    {
      title: "Message Graphs",
      subtitle: "When the conversation itself is the state",
      demo: M + "message_graph_bank_faq.py",
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
      demo: M + "streaming_stock_recommendation.py  ·  " + M + "langgraph.json",
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
`cd 14_advanced/07_langgraph
uv pip install "langgraph-cli[inmem]"
langgraph dev --tunnel     # opens Studio
# "domain not allowed"? Advanced settings →
#   Allowed domains: *.trycloudflare.com
# pick stock_news, input: hdfcbank
# Ctrl+C to stop` },
          ],
        ] },
        { type: "text", size: 11, color: "slate", text: "Studio shows the structure, runs the graph, lets you inspect state at every node, replay a run and edit prompts." },
      ],
    },
    {
      kind: "summary",
      title: "Module 07 Summary",
      subtitle: "What you built",
      built: [
        { tag: "graph", title: "A first graph", text: "Greeter: classify, branch, reply" },
        { tag: "route", title: "Conditional routing", text: "News sentiment and specialist routing" },
        { tag: "msgs", title: "A message graph", text: "A bank FAQ assistant over chat history" },
        { tag: "studio", title: "Streaming and Studio", text: "Watch the graph run, node by node" },
      ],
      takeaways: [
        "Use LangGraph when you need state, branches or loops",
        "State is the contract between nodes – design it first",
        "Nodes return partial updates, not the whole state",
        "Conditional edges turn a pipeline into a decision-maker",
        "Stream for responsiveness; use Studio to debug",
      ],
      next: "Module 08: LangGraph – Cycles, HIL and Persistence",
    },
  ],
};
