const M = "06_langchain_agents/";

module.exports = {
  section: "Module 06 – LangChain Agents and Tools",
  slides: [
    {
      kind: "opener",
      eyebrow: "Module 06",
      title: "LangChain Agents and Tool Use",
      subtitle: "Agents that reason, pick tools, act and observe – and the runtime that drives the loop",
      goals: [
        { icon: "FaRobot", title: "Explain what makes an agent", text: "perception, reasoning, action, observation" },
        { icon: "FaShapes", title: "Use ReAct and plan-and-execute", text: "and know when each one fits" },
        { icon: "FaScrewdriverWrench", title: "Create and bind custom tools", text: "@tool, bind_tools and Pydantic schemas" },
        { icon: "FaDatabase", title: "Connect agents to real systems", text: "AgentExecutor, SQL databases, chained tools" },
      ],
      agenda: [
        "Agent fundamentals and elements",
        "The ReAct pattern",
        "The plan-and-execute pattern",
        "Tool calling and custom tools",
        "Tools with Pydantic schemas",
        "AgentExecutor",
        "SQLDatabaseToolkit agents",
        "Multi-step reasoning: chaining tools",
      ],
    },
    {
      title: "Agent Fundamentals",
      subtitle: "Unlike a chatbot, an agent makes decisions and performs tasks until the goal is reached",
      demo: "Concept",
      blocks: [
        { type: "flow", loop: "continue until the goal is achieved", items: [
          { icon: "FaEye", label: "Perceive", caption: "Read the environment" },
          { icon: "FaBrain", label: "Reason", caption: "Think about the problem" },
          { icon: "FaSignsPost", label: "Decide", caption: "Choose the next action" },
          { icon: "FaScrewdriverWrench", label: "Act", caption: "Execute it with a tool" },
          { icon: "FaMagnifyingGlassChart", label: "Observe", caption: "Look at the result" },
        ] },
        { type: "tiles", cols: 4, size: 10, items: [
          { icon: "FaEye", title: "Perception", text: "Requests, documents, records, images, API and tool outputs" },
          { icon: "FaBrain", title: "Reasoning", text: "What's the goal? Which tool? Enough info? What first?" },
          { icon: "FaHandPointer", title: "Action", text: "Search, query a DB, send email, run code, call an API" },
          { icon: "FaMagnifyingGlass", title: "Observation", text: "Did it work? Was it useful? Another tool? Done?" },
        ] },
      ],
    },
    {
      title: "ReAct and Plan-and-Execute",
      subtitle: "Two ways to organise the loop – both built here as LangChain agents",
      demo: M + "react_agent_web_search_python_repl.py, plan_and_execute_agent.py",
      blocks: [
        { type: "compare", size: 11, cols: [
          { title: "ReAct – reason + act", color: "navy", items: [
            "Thought → Action → Observation, repeated until the answer",
            "Decides each step from the latest observation",
            "Demo tools: web search and a Python REPL",
            "Great when the path is not known in advance",
          ] },
          { title: "Plan-and-execute", color: "teal", items: [
            "Goal → Planner → Plan → Executor → Steps → Answer",
            "The plan is made once, up front",
            "Each step runs as its own small ReAct loop",
            "Great for long, structured tasks",
          ] },
        ] },
        { type: "chain", items: ["Thought", "Action", "Observation", "Thought", "Action", "Observation", "Answer"], highlight: [1, 4] },
      ],
    },

    // ---------------------------------------------------------------- tools
    { kind: "image", src: "ai_tool_system.png", alt: "AI tool system at a glance", demo: M + "tool_calling.py" },
    {
      title: "Tool Calling: The LLM Asks, the App Acts",
      subtitle: "On its own, an LLM cannot query an API, send an email, read a database or run a function",
      demo: M + "tool_calling.py",
      blocks: [
        { type: "flow", items: [
          { icon: "FaUser", label: "User", caption: "\"Most downloaded Jane Austen book on Project Gutenberg?\"" },
          { icon: "FaBrain", label: "LLM decides", caption: "\"I need the book catalogue\"" },
          { icon: "FaFileCode", label: "Tool call", caption: "search_gutenberg_books(\"Jane Austen\")" },
          { icon: "FaGears", label: "App executes", caption: "Our code runs the function" },
          { icon: "FaReply", label: "Answer", caption: "LLM reads the result and replies" },
        ] },
        { type: "callout", eyebrow: "Key point", text: "The LLM never executes anything. It only generates a structured request; the application decides whether and how to run it." },
      ],
    },
    {
      title: "Tools in LangChain",
      subtitle: "Define with @tool, attach with bind_tools, and constrain inputs with Pydantic",
      demo: M + "tool_calling.py, " + M + "tool_calling_pydantic.py",
      left: [
        { type: "code", caption: "Define a tool and bind it to the LLM", code:
`from langchain_core.tools import tool

@tool
def search_gutenberg_books(query: str) -> str:
    """Search Project Gutenberg books."""
    ...

llm_with_tools = llm.bind_tools(
    [search_gutenberg_books])` },
      ],
      right: [
        { type: "code", caption: "Pydantic in, Pydantic out", code:
`class SearchGutenbergInput(BaseModel):
    query: str = Field(description="Title, author or subject")

@tool("search_gutenberg_books",
      args_schema=SearchGutenbergInput)
def search_gutenberg_books(query: str) -> str: ...

class BookAnswer(BaseModel):
    title: str
    author: str
    download_count: int

structured_llm = llm.with_structured_output(BookAnswer)` },
        { type: "text", size: 11, color: "slate", text: "Pydantic makes sure what goes to and from the LLM matches a schema – wrong types fail fast." },
      ],
    },
    {
      title: "AgentExecutor: The Runtime for the Loop",
      subtitle: "Calls the model, runs the tools it asks for, feeds the results back, and knows when to stop",
      demo: M + "agent_executor_serp_gutenberg.py",
      blocks: [
        { type: "steps", size: 11, items: [
          { title: "Call 1 – the model asks for a tool", text: "Question: \"Who wrote Pride and Prejudice?\" → `serp_search(query=…)`" },
          { title: "The executor runs the tool, not the model", text: "Looks up serp_search, executes it, gets the web results" },
          { title: "Results go back into context", text: "The (call, result) pair is added to `agent_scratchpad`; loop back to the model" },
          { title: "Call 2 – another tool", text: "Sees \"Jane Austen\" → `search_gutenberg_books(query=\"Jane Austen\")`" },
          { title: "Call 3 – a plain-text answer", text: "No tool call this time = AgentFinish; the loop ends and `result[\"output\"]` is returned" },
        ] },
      ],
    },
    {
      title: "Talking to Databases: SQLDatabaseToolkit",
      subtitle: "Natural language → SQL query → answer",
      demo: "03_llm_examples/create_sales_db.py → " + M + "sql_database_toolkit_agent.py",
      blocks: [
        { type: "text", text: "\"Which department has the highest average salary?\" – the agent inspects the schema, writes the SQL, runs it, fixes it if it fails, and explains the result." },
        { type: "tiles", cols: 2, items: [
          { icon: "FaTableList", title: "sql_db_list_tables", text: "Which tables exist?" },
          { icon: "FaSitemap", title: "sql_db_schema", text: "Columns of the chosen tables" },
          { icon: "FaPlay", title: "sql_db_query", text: "Run a SQL query" },
          { icon: "FaCircleCheck", title: "sql_db_query_checker", text: "Check a query before running it" },
        ] },
        { type: "callout", eyebrow: "Production tip", text: "Give the agent a read-only database user – an LLM that can write SQL can also write DELETE." },
      ],
    },
    {
      title: "Multi-Step Reasoning: Chaining Tools",
      subtitle: "\"Book the cheapest flight and email me the ticket\" – no single tool can do that",
      demo: M + "chaining_tool_outputs.py, " + M + "chaining_tool_outputs_flask.py",
      blocks: [
        { type: "flow", items: [
          { icon: "FaCity", label: "User city", caption: "Input" },
          { icon: "FaLocationDot", label: "geocode_city()", caption: "→ latitude / longitude" },
          { icon: "FaCloudSun", label: "get_current_weather()", caption: "uses the coordinates" },
          { icon: "FaMapPin", label: "find_nearby_places()", caption: "uses the coordinates" },
          { icon: "FaShirt", label: "recommend_clothing()", caption: "uses the weather" },
        ] },
        { type: "callout", eyebrow: "Tool chaining", text: "Tool 1 → output → Tool 2 → output → Tool 3 → final answer. The Flask app puts a UI on top of the chaining script." },
      ],
    },
    {
      kind: "summary",
      title: "Module 06 Summary",
      subtitle: "What you built",
      built: [
        { tag: "react", title: "A ReAct agent", text: "Web search plus a Python REPL" },
        { tag: "plan", title: "Plan-and-execute", text: "A planner and a step executor" },
        { tag: "tool", title: "Custom tools", text: "@tool, bind_tools and Pydantic schemas" },
        { tag: "SQL", title: "A SQL agent", text: "Questions over the sales database" },
      ],
      takeaways: [
        "The LLM requests tool calls; the executor runs them",
        "A clear docstring and schema make a tool usable",
        "ReAct for open paths, plan-and-execute for long tasks",
        "Chain tools when one output is the next one's input",
        "Restrict what tools can do (read-only DB, allow-lists)",
      ],
      next: "Module 07: LangGraph",
    },
  ],
};
