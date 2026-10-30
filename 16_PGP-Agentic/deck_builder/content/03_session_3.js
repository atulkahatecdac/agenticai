const S = "session_3/";

module.exports = {
  section: "Session 3 – LangChain Agents and Tools",
  slides: [
    {
      kind: "opener",
      eyebrow: "Session 3",
      title: "LangChain Agents and Tool Use",
      subtitle: "Prompting techniques that drive agents, custom tools, and agents connected to real systems",
      goals: [
        { icon: "FaPenToSquare", title: "Write prompts that steer agents", text: "personas, few-shot examples, chain-of-thought, ReAct" },
        { icon: "FaScrewdriverWrench", title: "Create and bind custom tools", text: "@tool, bind_tools, and Pydantic schemas" },
        { icon: "FaDatabase", title: "Connect agents to real systems", text: "SQL databases, chained tools and web research" },
      ],
      agenda: [
        "Agent fundamentals (recap)",
        "Prompting techniques that drive agents",
        "Creating custom tools and binding them to an LLM",
        "Tools with Pydantic schemas",
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
        { type: "callout", eyebrow: "This session", text: "The same loop, built with LangChain: prompts steer the Reason step, tools power the Act step, and a short loop in our own code ties them together." },
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
        { type: "code", caption: "Example from the demo (REACT_INSTRUCTIONS)", code:
`You are a customer-support assistant that decides
refund eligibility using ReAct-style reasoning.
You do NOT know order details in advance -
you must look them up.` },
      ],
    },
    {
      title: "Zero-Shot, One-Shot and Few-Shot Prompting",
      subtitle: "The same refund decision for order A1002, with examples or with none at all",
      demo: S + "3_1_prompting_techniques.py",
      blocks: [
        { type: "cards", size: 10.5, codeSize: 8.5, items: [
          { n: 0, title: "Zero-shot", tag: "Policy and case only", lines: ["**Best for:** QA, summaries, translation, simple classification", "**Watch out:** inconsistent on complex tasks"],
            code: `Headphones, 42 days, opened,
undamaged. Eligible for a
refund? Yes/No and amount.` },
          { n: 1, title: "One-shot", tag: "One example", lines: ["**Best for:** teaching a format or style", "**Watch out:** one example rarely covers every case"],
            code: `Desk Lamp, 10 days, unopened
→ Yes, refund of $19.99
Headphones, 42 days…
→ ?` },
          { n: "2+", title: "Few-shot", tag: "Three examples here", lines: ["**Best for:** complex classification, extraction, structured output", "**Watch out:** longer prompts cost tokens and time"],
            code: `Desk Lamp, unopened → Yes
Coffee Mug, damaged → No
Yoga Mat, 35 days → No
Headphones, 42 days… → ?` },
        ] },
      ],
    },
    {
      title: "Chain-of-Thought and Tree-of-Thought Prompting",
      subtitle: "Ask the model to reason step by step, or to compare several lines of reasoning",
      demo: S + "3_1_prompting_techniques.py",
      blocks: [
        { type: "text", text: "**Case:** \"I'd like to return order A1002. Can I get a refund?\" Bluetooth Headphones, delivered 42 days ago, opened but undamaged. The policy allows returns within 30 days." },
        { type: "compare", size: 11, cols: [
          { title: "Zero-shot: answer directly", color: "slate", items: [
            "\"No, this order is not eligible.\"",
            "Plausible – but we cannot see or check the reasoning",
          ] },
          { title: "CoT: \"Think through the policy step by step\"", color: "teal", items: [
            "First the window: 42 days is past the 30-day limit",
            "Then the condition: opened but undamaged is acceptable",
            "**Final Decision:** not eligible, because of the window",
          ] },
        ] },
        { type: "callout", eyebrow: "Tree-of-thought", text: "Three separate calls each explore one line of reasoning (temperature 0.9); a final call evaluates them against the policy and gives one decision." },
      ],
    },
    {
      title: "ReAct Prompting",
      subtitle: "Reason + Act: alternate thinking with tool calls, and use each result to decide the next step\nWe have discussed this in Section 1, earlier; but now want to see the inside working of the loop",
      demo: S + "3_1_prompting_techniques.py",
      split: [1, 1.35],
      left: [
        { type: "text", text: "**User:** I'd like to return order A1003. Can I get a refund?" },
        { type: "chain", items: ["Question", "Thought", "Action", "Observation", "Thought", "Answer"], highlight: [2] },
      ],
      right: [
        { type: "steps", size: 10.5, titleSize: 11.5, gap: 0.09, items: [
          { n: "T", title: "Thought: I don't know this order yet, so I must look it up" },
          { n: "A", title: "Action: lookup_order[A1003]", color: "navy" },
          { n: "O", title: "Observation: Laptop Stand, 6 days since delivery, opened, damaged, $34.5", color: "teal" },
          { n: "T", title: "Thought: within 30 days, but the policy excludes opened and damaged items" },
          { n: "✓", title: "Final Answer: No, this order is not eligible for a refund", color: "slate" },
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
      title: "Talking to Databases: SQLDatabaseToolkit",
      subtitle: "Natural language → SQL query → answer",
      demo: S + "3_4_create_sales_db.py → 3_5_sql_database_toolkit_agent.py, 3_6_sales_db_agent.py",
      blocks: [
        { type: "text", text: "\"Which product generated the highest total revenue?\" – the agent inspects the schema, writes the SQL, runs it and explains the result. `3_6` asks the same kind of question with one hand-written `run_sql` tool on the OpenAI Agents SDK." },
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
      title: "The Agent Loop, in Our Own Code",
      subtitle: "The bind_tools idea from 3_2, repeated until the LLM stops asking for tools",
      demo: S + "3_5_sql_database_toolkit_agent.py, 3_7_chaining_tool_outputs.py",
      split: [1.35, 1],
      left: [
        { type: "code", caption: "run_agent() from 3_5 (prints and try/except left out)", code:
`def run_agent(question, max_steps=8):
    messages = [SystemMessage(SYSTEM_PROMPT),
                HumanMessage(question)]

    for _ in range(max_steps):
        ai_message = llm_with_tools.invoke(messages)
        messages.append(ai_message)

        if not ai_message.tool_calls:
            return ai_message.content

        for tool_call in ai_message.tool_calls:
            tool = tools_by_name[tool_call["name"]]
            result = tool.invoke(tool_call["args"])
            messages.append(ToolMessage(
                content=str(result),
                tool_call_id=tool_call["id"]))` },
      ],
      right: [
        { type: "steps", size: 10.5, titleSize: 11.5, items: [
          { title: "Ask the LLM", text: "It sees the question and all results so far" },
          { title: "No tool calls?", text: "Then this is the final answer, so stop" },
          { title: "Run the tools", text: "Our code runs them, not the LLM" },
          { title: "Feed the results back", text: "Each ToolMessage goes into the history; loop again" },
          { title: "Limit the steps", text: "max_steps stops a confused agent from looping forever" },
        ] },
      ],
    },
    {
      title: "Multi-Step Reasoning: Chaining Tools",
      subtitle: "\"What should I wear outside today in Tokyo?\" – no single tool can answer that",
      demo: S + "3_7_chaining_tool_outputs.py, 3_8_chaining_tool_outputs_flask.py",
      blocks: [
        { type: "flow", items: [
          { icon: "FaCity", label: "User city", caption: "Input" },
          { icon: "FaLocationDot", label: "geocode_city()", caption: "→ latitude / longitude" },
          { icon: "FaCloudSun", label: "get_current_weather()", caption: "uses the coordinates" },
          { icon: "FaShirt", label: "recommend_clothing()", caption: "uses the weather" },
          { icon: "FaMapPin", label: "find_nearby_places()", caption: "uses the coordinates" },
        ] },
        { type: "callout", eyebrow: "Two ways", text: "3_7 runs this twice: first the agent decides each next tool, then the same chain is hardcoded with no LLM. The Flask app (3_8) puts a UI on the hardcoded version." },
      ],
    },
    {
      title: "Tool-Augmented Research Agent",
      subtitle: "Search the web, dig deeper where needed, and save a report of what it found",
      demo: S + "3_9_research_agent_tools.py, 3_10_research_agent_tools_serp.py",
      blocks: [
        { type: "flow", items: [
          { icon: "FaCalendarDays", label: "get_current_date()", caption: "When the topic depends on recency" },
          { icon: "FaMagnifyingGlass", label: "web_search()", caption: "Tavily (3_9) or SerpAPI (3_10)" },
          { icon: "FaCode", label: "fetch_page_content()", caption: "BeautifulSoup reads promising pages" },
          { icon: "FaFileLines", label: "save_report()", caption: "Markdown file with sources" },
        ] },
        { type: "callout", eyebrow: "Different framework", text: "These two demos use the OpenAI Agents SDK from Session 1, not LangChain. The agent decides the tool order, and the script then checks that the report file really exists." },
      ],
    },
    {
      kind: "summary",
      title: "Session 3 Summary",
      subtitle: "What you built today",
      built: [
        { tag: "3_1", title: "Prompting techniques", text: "Few-shot, chain-of-thought, tree-of-thought and ReAct" },
        { tag: "3_2", title: "Custom tools", text: "@tool, bind_tools and Pydantic input schemas" },
        { tag: "3_5", title: "SQL agent", text: "Natural-language questions, with our own agent loop" },
        { tag: "3_7", title: "Tool chaining", text: "One tool's output becomes the next tool's input" },
        { tag: "3_9", title: "Research agent", text: "Search, scrape and summarise" },
      ],
      takeaways: [
        "Prompts are the agent's operating manual – structure them",
        "The LLM requests tool calls; your code runs them",
        "A clear docstring and schema are what make a tool usable",
        "Chain tools when one output is the next one's input",
        "Restrict what tools can do (read-only DB, allow-lists)",
      ],
      next: "Session 4: LangGraph – Stateful Workflows and Routing",
    },
  ],
};
