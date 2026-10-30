const S = "session_7/";

module.exports = {
  section: "Session 7 – AutoGen",
  slides: [
    {
      kind: "opener",
      eyebrow: "Session 7",
      title: "Multi-Agent Systems with Microsoft AutoGen",
      subtitle: "Agents that cooperate by talking to each other – in teams, group chats and graphs",
      goals: [
        { icon: "FaRobot", title: "Build AssistantAgents with tools", text: "model clients, messages, streaming" },
        { icon: "FaBolt", title: "Run agents sync and async", text: "and get structured, multimodal output" },
        { icon: "FaComments", title: "Organise agents into teams", text: "round-robin, selector and Magentic-One group chats" },
        { icon: "FaDiagramProject", title: "Control the conversation as a graph", text: "GraphFlow with parallel branches and joins; memory" },
      ],
      agenda: [
        "AutoGen overview",
        "AssistantAgent and tools",
        "Synchronous vs asynchronous agents",
        "Structured output",
        "Multimodal messages",
        "Teams / group chats: round-robin, selector, magentic",
        "GraphFlow (including parallel join)",
        "Memory",
      ],
    },
    {
      title: "AutoGen at a Glance",
      subtitle: "Microsoft's open-source framework for agents that cooperate – fully asynchronous since v0.4",
      demo: S + "7_1_autogen_basic.py",
      blocks: [
        { type: "cards", size: 10.5, items: [
          { icon: "FaWindowMaximize", title: "AutoGen Studio", tag: "No-code UI", lines: ["Web UI to prototype agents by drag and drop and watch them interact", "**Use when:** demoing ideas or validating a workflow before coding"] },
          { icon: "FaComments", title: "AgentChat", tag: "What we use", lines: ["High-level Python API for single- and multi-agent conversational apps", "**Use when:** dialogue and turn-taking matter most"] },
          { icon: "FaMicrochip", title: "Core", tag: "Low level", lines: ["Event-driven runtime: agents, messages, handlers at scale", "**Use when:** many agents coordinate beyond simple chats"] },
        ] },
        { type: "callout", eyebrow: "In this session", text: "Every demo uses AgentChat (packages autogen-agentchat and autogen-ext) with an OpenAI model client – except 7_5, which uses Anthropic Claude." },
      ],
    },
    {
      title: "The AutoGen Demos",
      subtitle: "One concept per script, building up from a single agent to teams and graphs",
      demo: S + "7_1_* … 7_14_*",
      blocks: [
        { type: "cols", cols: [
          [{ type: "table", size: 10, widths: [3.1, 0.9], head: ["What it adds", "Script"], rows: [
            ["Basic AssistantAgent syntax", "7_1"],
            ["Calls a live forex API as a tool", "7_2"],
            ["Sends a TextMessage instead of a plain task", "7_3"],
            ["Two agents, run one after the other", "7_4"],
            ["Two agents in parallel – Claude + Yahoo Finance", "7_5"],
            ["Structured output (OpenAI models)", "7_6"],
            ["MultiModalMessage – text plus an image", "7_7"],
          ] }],
          [{ type: "table", size: 10, widths: [3.1, 0.9], head: ["What it adds", "Script"], rows: [
            ["Round-robin group chat", "7_8"],
            ["Selector group chat", "7_9"],
            ["Magentic-One group chat", "7_10"],
            ["Fact-check: \"India never faced a recession in 30 years\"", "7_11"],
            ["GraphFlow", "7_12"],
            ["GraphFlow with a parallel join", "7_13"],
            ["Memory", "7_14"],
          ] }],
        ] },
      ],
    },
    {
      title: "AssistantAgent",
      subtitle: "An LLM-backed agent that can call Python functions as tools",
      demo: S + "7_2_autogen_forex_api.py, 7_3_autogen_forex_api_text_message.py",
      split: [1, 1.15],
      left: [
        { type: "code", caption: "7_2_autogen_forex_api.py", code:
`agent = AssistantAgent(
    name="forex_agent",
    model_client=OpenAIChatCompletionClient(
        model="gpt-4o-mini"),
    tools=[get_forex_rate],
)

async def main():
    await Console(agent.run_stream(
        task="What is the current forex rate of USD to INR?"))

asyncio.run(main())` },
      ],
      right: [
        { type: "table", size: 10, widths: [1.6, 2.6], head: ["Parameter", "What it does"], rows: [
          ["`name`", "Identifies the agent among many"],
          ["`model_client`", "The LLM backend that powers it"],
          ["`tools`", "Python functions – converted to FunctionTools with a schema automatically"],
          ["`system_message`", "Role, tone and purpose"],
          ["`reflect_on_tool_use`", "Adds a self-check after tool calls"],
          ["`model_client_stream`", "Streams tokens as they arrive"],
        ] },
      ],
    },
    {
      title: "How a TextMessage Travels",
      subtitle: "From the user to the model and back, wrapped in message objects",
      demo: S + "7_3_autogen_forex_api_text_message.py",
      blocks: [
        { type: "flow", items: [
          { icon: "FaUser", label: "Create", caption: "TextMessage(content=…, source=\"User\")" },
          { icon: "FaInbox", label: "Receive", caption: "agent.run_stream(task=text_message.content)" },
          { icon: "FaRightLeft", label: "Convert", caption: "to_model_message() – automatic" },
          { icon: "FaMicrochip", label: "Model", caption: "The model client generates a reply" },
          { icon: "FaReply", label: "Wrap", caption: "TextMessage(content=\"1 USD = 83.12 INR\", source=\"forex_agent\")" },
        ] },
        { type: "callout", eyebrow: "Why bother", text: "Message objects carry who sent what – essential once several agents are talking in the same conversation." },
      ],
    },
    {
      title: "Synchronous vs Asynchronous Agents",
      subtitle: "The Session 1 idea again, now with AutoGen agents",
      demo: S + "7_4_autogen_synchronous_agents.py, 7_5_autogen_asynchronous_agents.py",
      blocks: [
        { type: "compare", size: 11, codeSize: 9, cols: [
          { title: "Sequential", color: "navy", items: ["Each agent finishes before the next starts", "Use when later steps need earlier outputs", "Simple to reason about; slower on I/O"], code:
`desc = await desc_agent.on_messages([...])
ctx  = await context_agent.on_messages([...])` },
          { title: "Concurrent", color: "teal", items: ["Independent agents run together", "Use when tasks don't depend on each other", "Faster; shared state is harder to manage"], code:
`stock_task = asyncio.create_task(
    stock_return_agent.on_messages(...))
index_task = asyncio.create_task(
    index_return_agent.on_messages(...))
await asyncio.gather(stock_task, index_task)` },
        ] },
      ],
    },
    {
      title: "Structured Output",
      subtitle: "Make the model return JSON that matches a schema, ready for the next step",
      demo: S + "7_6_autogen_structured_output.py",
      blocks: [
        { type: "flow", items: [
          { icon: "FaFileLines", label: "5 job postings", caption: "Unstructured description text (Kaggle LinkedIn jobs)" },
          { icon: "FaRobot", label: "Extraction agent", caption: "Reads each description" },
          { icon: "FaTableList", label: "Pydantic schema", caption: "company_name, role, location", color: "coral" },
          { icon: "FaFileCode", label: "JSON out", caption: "Consistent, easy to parse" },
        ] },
        { type: "text", size: 11.5, color: "slate", text: "Currently supported with OpenAI models. The schema guarantees the downstream code always gets the same keys." },
      ],
    },
    {
      title: "Teams: Agents Talking to Agents",
      subtitle: "Who speaks next is what distinguishes the team types",
      demo: S + "7_8_…_round_robin_group_chat.py, 7_9_…_selector_….py, 7_10_…_magentic_….py",
      blocks: [
        { type: "cards", size: 10, items: [
          { icon: "FaArrowsSpin", title: "Round-robin", lines: ["Agents take turns in a fixed order; everyone sees everything", "**e.g.** primary and critic refine a text until the critic says STOP"] },
          { icon: "FaHandPointer", title: "Selector", lines: ["An LLM picks the next speaker after each message", "**e.g.** Reviewer, Coder and Tester – whoever is needed next"] },
          { icon: "FaWandMagicSparkles", title: "Magentic-One", lines: ["A general-purpose team for open-ended tasks over web and files", "**e.g.** extract, summarise, analyse and review a PDF"] },
          { icon: "FaRightLeft", title: "Swarm", lines: ["Agents hand off control with HandoffMessage", "**e.g.** a DataCollector passes results to a DataAnalyzer (no demo)"] },
        ] },
      ],
    },
    {
      title: "GraphFlow: Conversations as a Directed Graph",
      subtitle: "Like LangGraph, for AutoGen teams – sequential, parallel and conditional paths",
      demo: S + "7_12_autogen_graphflow.py, 7_13_autogen_graphflow_parallel_join.py",
      split: [1, 1.05],
      left: [
        { type: "icons", d: 0.36, size: 11, items: [
          { icon: "FaCircleDot", title: "Nodes are agents", text: "Edges are the allowed transitions, optionally conditional" },
          { icon: "FaCodeBranch", title: "Branches, loops, joins", text: "Fan out to parallel agents, then join" },
          { icon: "FaFlagCheckered", title: "Explicit termination", text: "Max turns, a stop signal, or graph completion" },
          { icon: "FaTriangleExclamation", title: "Still experimental", text: "Expect API changes; design termination carefully" },
        ] },
      ],
      right: [
        { type: "code", caption: "7_13: two editors in parallel, one reviewer", code:
`builder = DiGraphBuilder()
builder.add_node(writer).add_node(editor1) \\
       .add_node(editor2).add_node(final_reviewer)
builder.add_edge("writer", "editor1")
builder.add_edge("writer", "editor2")
builder.add_edge("editor1", "final_reviewer")
builder.add_edge("editor2", "final_reviewer")
flow = GraphFlow(participants=builder.get_participants(),
                 graph=builder.build())` },
      ],
    },
    {
      title: "Memory in AutoGen",
      subtitle: "Store facts and inject the relevant ones into the agent's context",
      demo: S + "7_14_autogen_memory.py",
      split: [1, 1.1],
      left: [
        { type: "code", caption: "7_14_autogen_memory.py (condensed)", code:
`user_memory = ListMemory()
assistant_agent = AssistantAgent(
    name="multilingual_assistant",
    model_client=client,
    memory=[user_memory],
)

preferred_language = input("...preferred language...")
await user_memory.add(MemoryContent(
    content=f"The user prefers replies in {preferred_language}.",
    mime_type=MemoryMimeType.TEXT))` },
      ],
      right: [
        { type: "table", size: 10, widths: [1.4, 2.6], head: ["Piece", "What it does"], rows: [
          ["`add()`", "Store a fact"],
          ["`query()`", "Retrieve relevant facts"],
          ["`update_context()`", "Inject them into the agent's context"],
          ["`clear()` / `close()`", "Start fresh / release resources"],
          ["ListMemory", "Simple chronological list – demos, small tasks"],
          ["Vector memory", "Semantic search in a vector DB – RAG-style"],
        ] },
      ],
    },
    {
      kind: "summary",
      title: "Session 7 Summary",
      subtitle: "What you built today",
      built: [
        { tag: "7_2", title: "A tool-using agent", text: "AssistantAgent calling a live forex API" },
        { tag: "7_5", title: "Parallel agents", text: "Claude and Yahoo Finance agents run concurrently" },
        { tag: "7_6", title: "Structured extraction", text: "Job postings → JSON via a Pydantic schema" },
        { tag: "7_8", title: "Group chats", text: "Round-robin, selector and Magentic-One teams" },
        { tag: "7_13", title: "GraphFlow", text: "Parallel editors joined by a final reviewer" },
      ],
      takeaways: [
        "AutoGen models collaboration as conversation between agents",
        "Everything is async – use it to run independent agents together",
        "Team type = the rule for who speaks next",
        "GraphFlow brings explicit, graph-shaped control to teams",
        "Memory is just context the framework injects for you",
      ],
      next: "Session 8: Agentic RAG and GraphRAG for Agents",
    },
  ],
};
