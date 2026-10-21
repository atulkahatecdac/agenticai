const S = "session_3/";

module.exports = {
  section: "Session 3 – LangChain Agents and Tools",
  slides: [
    {
      kind: "opener",
      eyebrow: "Session 3  ·  Sun 31-Oct  ·  08:00–11:00 AM",
      title: "LangChain Agents and Tool Use",
      subtitle: "Prompting techniques that drive agents, custom tools, and the executors that run the loop",
      goals: [
        { icon: "FaPenToSquare", title: "Write prompts that steer agents", text: "personas, few-shot examples, chain-of-thought, ReAct" },
        { icon: "FaScrewdriverWrench", title: "Create and bind custom tools", text: "@tool, bind_tools, and Pydantic schemas" },
        { icon: "FaArrowsRotate", title: "Run the agent loop", text: "AgentExecutor, ReAct and plan-and-execute agents" },
        { icon: "FaDatabase", title: "Connect agents to real systems", text: "SQL databases, chained tools and web research" },
      ],
      agenda: [
        "Agent fundamentals (recap)",
        "Prompting techniques that drive agents",
        "Creating custom tools and binding them to an LLM",
        "Tools with Pydantic schemas",
        "AgentExecutor",
        "ReAct agent",
        "Plan-and-Execute agent",
        "SQL database agents",
        "Multi-step reasoning and tool chaining",
        "Tool-augmented research agent",
      ],
    },
    {
      title: "Agent Fundamentals: A Quick Recap",
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
        { type: "callout", eyebrow: "This session", text: "The same loop, built with LangChain: prompts steer the Reason step, tools power the Act step, and an executor runs the loop." },
      ],
    },

    // ---------------------------------------------------------------- prompting
    {
      title: "System Prompts for Domain-Expert Personas",
      subtitle: "Set the role, expertise, rules and style before any user interaction",
      demo: S + "3_1_prompting_techniques.py",
      split: [1, 1.25],
      left: [
        { type: "table", size: 10.5, widths: [1.3, 2.6], head: ["Component", "Purpose"], rows: [
          ["Role", "The assistant's expertise"],
          ["Goal", "The primary objective"],
          ["Knowledge scope", "Domain or information sources"],
          ["Instructions", "How to generate answers"],
          ["Constraints", "What to avoid"],
          ["Output format", "Shape of the response"],
          ["Tone", "Formal, friendly, technical …"],
        ] },
      ],
      right: [
        { type: "code", caption: "Template", code:
`You are an expert <ROLE>.
Your goal is to <OBJECTIVE>.
Use your expertise in <DOMAIN>.
When answering:
- Explain concepts clearly.
- Ask clarifying questions if information is missing.
- Do not make up facts. If uncertain, say so.
Respond in a professional and concise manner.` },
        { type: "code", caption: "Example", code:
`You are an experienced physician specialising
in internal medicine. Always:
- Explain medical terminology simply.
- Recommend a professional for emergencies.
- Do not diagnose with certainty from limited data.` },
      ],
    },
    {
      title: "Zero-Shot, One-Shot and Few-Shot Prompting",
      subtitle: "Show the model examples of what you want – or none at all",
      demo: S + "3_1_prompting_techniques.py",
      blocks: [
        { type: "cards", size: 10.5, codeSize: 8.5, items: [
          { n: 0, title: "Zero-shot", tag: "Instruction only", lines: ["**Best for:** QA, summaries, translation, simple classification", "**Watch out:** inconsistent on complex tasks"],
            code: `Classify the sentiment:
"Arrived on time, works
perfectly."` },
          { n: 1, title: "One-shot", tag: "One example", lines: ["**Best for:** teaching a format or style", "**Watch out:** one example rarely covers every case"],
            code: `Review: Terrible phone.
→ Negative
Review: Arrived on time…
→ ?` },
          { n: "2+", title: "Few-shot", tag: "2–10 examples", lines: ["**Best for:** complex classification, extraction, structured output", "**Watch out:** longer prompts cost tokens and time"],
            code: `Excellent service. → Positive
Very slow delivery. → Negative
Damaged packaging. → Negative
Arrived on time… → ?` },
        ] },
      ],
    },
    {
      title: "Chain-of-Thought (CoT) Prompting",
      subtitle: "Ask the model to reason step by step before it answers",
      demo: S + "3_1_prompting_techniques.py",
      blocks: [
        { type: "text", text: "**Prompt:** A customer has a budget of $1,200 and needs a laptop for programming, machine learning and occasional gaming. Recommend the best option." },
        { type: "compare", size: 11, cols: [
          { title: "Without CoT", color: "slate", items: [
            "\"I recommend Laptop B because it offers the best balance of CPU, GPU, memory and price.\"",
            "Plausible – but we cannot see or check the reasoning",
          ] },
          { title: "With CoT: \"Reason step by step first\"", color: "teal", items: [
            "Budget limit is $1,200",
            "Programming needs a fast CPU and 16 GB+ RAM",
            "ML and gaming both need a dedicated GPU",
            "Laptop B: i7, 16 GB, RTX 4060, 1 TB SSD – $1,180",
            "**So:** Laptop B meets every requirement within budget",
          ] },
        ] },
      ],
    },
    {
      title: "ReAct Prompting",
      subtitle: "Reason + Act: alternate thinking with tool calls, and use each result to decide the next step",
      demo: S + "3_1_prompting_techniques.py",
      split: [1, 1.35],
      left: [
        { type: "text", text: "**User:** I have ₹10 lakh to invest for 10 years. Equity mutual fund, fixed deposit or balanced fund?" },
        { type: "chain", items: ["Question", "Thought", "Action", "Observation", "Thought", "Answer"], highlight: [2] },
      ],
      right: [
        { type: "steps", size: 10.5, titleSize: 11.5, gap: 0.09, items: [
          { n: "T", title: "Thought: I need the user's risk profile" },
          { n: "A", title: "Action: getCustomerProfile(id)", color: "navy" },
          { n: "O", title: "Observation: age 38, moderate risk, 10-year horizon", color: "teal" },
          { n: "T", title: "Thought: compare returns and risk of the options" },
          { n: "A", title: "Action: getInvestmentOptions([...])", color: "navy" },
          { n: "O", title: "Observation: equity 12% high · FD 7% low · balanced 10% medium", color: "teal" },
          { n: "✓", title: "Answer: a balanced fund suits a moderate risk profile over 10 years", color: "slate" },
        ] },
      ],
    },

    // ---------------------------------------------------------------- tools
    {
      title: "Tool Calling: The LLM Asks, the App Acts",
      subtitle: "On its own, an LLM cannot query an API, send an email, read a database or run a function",
      demo: S + "3_2_tool_calling.py",
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
      demo: S + "3_2_tool_calling.py, 3_3_tool_calling_pydantic.py",
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
        { type: "code", caption: "Pydantic in, Pydantic out (3_3)", code:
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
      demo: S + "3_4_agent_executor_serp_gutenberg.py",
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
      title: "ReAct and Plan-and-Execute in LangChain",
      subtitle: "The two patterns from Session 1, now built with LangChain agents",
      demo: S + "3_5_react_agent_web_search_python_repl.py, 3_6_plan_and_execute_agent.py",
      blocks: [
        { type: "compare", size: 11, cols: [
          { title: "ReAct agent – 3_5", color: "navy", items: [
            "Thought → Action → Observation, repeated",
            "Tools: web search and a Python REPL",
            "Decides each step from the latest observation",
            "Great when the path is not known in advance",
          ] },
          { title: "Plan-and-execute agent – 3_6", color: "teal", items: [
            "Goal → Planner → Plan → Executor → Steps → Answer",
            "The plan is made once, up front",
            "Each step runs as its own small ReAct loop",
            "Great for long, structured tasks",
          ] },
        ] },
      ],
    },
    {
      title: "Talking to Databases: SQLDatabaseToolkit",
      subtitle: "Natural language → SQL query → answer",
      demo: S + "3_7_create_sales_db.py → 3_8_sql_database_toolkit_agent.py, 3_9_sales_db_agent.py",
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
      demo: S + "3_10_chaining_tool_outputs.py, 3_11_chaining_tool_outputs_flask.py",
      blocks: [
        { type: "flow", items: [
          { icon: "FaCity", label: "User city", caption: "Input" },
          { icon: "FaLocationDot", label: "geocode_city()", caption: "→ latitude / longitude" },
          { icon: "FaCloudSun", label: "get_current_weather()", caption: "uses the coordinates" },
          { icon: "FaMapPin", label: "find_nearby_places()", caption: "uses the coordinates" },
          { icon: "FaShirt", label: "recommend_clothing()", caption: "uses the weather" },
        ] },
        { type: "callout", eyebrow: "Tool chaining", text: "Tool 1 → output → Tool 2 → output → Tool 3 → final answer. The Flask app (3_11) puts a UI on top of the chaining script (3_10)." },
      ],
    },
    {
      title: "Tool-Augmented Research Agent",
      subtitle: "Search the web, dig deeper where needed, and write up what it found",
      demo: S + "3_12_research_agent_tools.py, 3_13_research_agent_tools_serp.py",
      blocks: [
        { type: "flow", items: [
          { icon: "FaMagnifyingGlass", label: "Search", caption: "SERP API on the topic" },
          { icon: "FaCalendarDays", label: "Recent?", caption: "Use date-based search for fresh topics" },
          { icon: "FaCode", label: "Dig deeper", caption: "BeautifulSoup reads specific pages" },
          { icon: "FaFileLines", label: "Report", caption: "Summarise with sources" },
        ] },
      ],
    },
    {
      kind: "summary",
      title: "Session 3 Summary",
      subtitle: "What you built today",
      built: [
        { tag: "3_1", title: "Prompting techniques", text: "Personas, few-shot, chain-of-thought and ReAct prompts" },
        { tag: "3_2", title: "Custom tools", text: "@tool, bind_tools and Pydantic input schemas" },
        { tag: "3_4", title: "AgentExecutor", text: "The tool loop with web search and Gutenberg tools" },
        { tag: "3_8", title: "SQL agent", text: "Natural-language questions over a sales database" },
        { tag: "3_12", title: "Research agent", text: "Search, scrape and summarise" },
      ],
      takeaways: [
        "Prompts are the agent's operating manual – structure them",
        "The LLM requests tool calls; the executor runs them",
        "A clear docstring and schema are what make a tool usable",
        "Chain tools when one output is the next one's input",
        "Restrict what tools can do (read-only DB, allow-lists)",
      ],
      next: "Session 4: LangGraph – Stateful Workflows and Routing",
    },
  ],
};
