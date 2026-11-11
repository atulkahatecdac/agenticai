const MCP = "11_mcp_advanced/";

module.exports = {
  section: "Module 11 – MCP Ecosystem Integrations",
  slides: [
    {
      kind: "opener",
      eyebrow: "Module 11",
      title: "MCP Ecosystem Integrations",
      subtitle: "Ready-made MCP servers for databases, files, GitHub and browsers – and agents that use several at once",
      goals: [
        { icon: "FaCubes", title: "Know where servers come from", text: "official, community and enterprise" },
        { icon: "FaDatabase", title: "Use ready-made servers", text: "SQLite, filesystem, GitHub, Playwright" },
        { icon: "FaDiagramProject", title: "Give MCP tools to agents", text: "LangChain, LangGraph and CrewAI" },
        { icon: "FaServer", title: "Plan for production", text: "server layout, gateways, auth, monitoring" },
      ],
      agenda: [
        "Official, community and enterprise servers",
        "SQLite MCP server",
        "Filesystem MCP server",
        "GitHub MCP server: tokens and Claude Desktop",
        "Playwright MCP server",
        "MCP with LangChain and LangGraph",
        "MCP with CrewAI",
        "A two-server report pipeline",
        "MCP in production",
      ],
    },
    {
      title: "Where MCP Servers Come From",
      subtitle: "Before writing a server, check whether one already exists",
      demo: "Concept",
      blocks: [
        { type: "cards", size: 10.5, items: [
          { icon: "FaCertificate", title: "Official", tag: "Product owners", lines: ["Built by the product's creators or trusted organisations", "Filesystem, Git, Fetch", "github.com/modelcontextprotocol/servers"] },
          { icon: "FaUsers", title: "Community", tag: "Open source", lines: ["Servers for popular services", "Google Drive, Slack, Notion, Jira, PostgreSQL, SQLite, Redis, flight search"] },
          { icon: "FaBuilding", title: "Enterprise", tag: "Private", lines: ["Internal servers in front of company systems", "HR, CRM, ERP, customer database, banking"] },
        ] },
      ],
    },
    {
      title: "SQLite MCP Server",
      subtitle: "A local, standard bridge between AI clients and a SQLite database",
      demo: MCP + "11_1_sqlite_resource_mcp_client.py",
      split: [1, 1.15],
      left: [
        { type: "steps", size: 10.5, items: [
          { title: "Launch the server", text: "Pointed at one database file" },
          { title: "ClientSession.initialize()", text: "The MCP handshake" },
          { title: "list_tools()", text: "Discover what the server offers – nothing hard-coded" },
          { title: "Call the tools", text: "No connection or cursor handling in the client" },
        ] },
      ],
      right: [
        { type: "tiles", cols: 1, size: 10.5, titleSize: 11.5, items: [
          { icon: "FaTable", title: "create_table", text: "Run DDL to create tables" },
          { icon: "FaPen", title: "write_query", text: "INSERT, UPDATE, DELETE" },
          { icon: "FaMagnifyingGlass", title: "read_query", text: "SELECT statements" },
          { icon: "FaListUl", title: "list_tables / describe_table", text: "Enumerate tables; inspect columns" },
        ] },
      ],
    },
    {
      title: "Filesystem MCP Server",
      subtitle: "Safe, scoped access to local files – no custom file-handling code in the client",
      demo: MCP + "11_2_filesystem_mcp_client.py",
      split: [1, 1.1],
      left: [
        { type: "icons", d: 0.38, size: 11, items: [
          { icon: "FaFolderOpen", title: "Allowed roots", text: "The server starts with one or more allowed directories as arguments" },
          { icon: "FaLock", title: "Sandboxed", text: "Every operation stays inside those roots" },
          { icon: "FaBan", title: "Outside paths are rejected", text: "No arbitrary filesystem access", color: "coral" },
        ] },
      ],
      right: [
        { type: "text", text: "**Tools exposed**", size: 12 },
        { type: "chain", size: 10, items: ["read_file", "read_multiple_files", "write_file", "edit_file", "create_directory", "list_directory", "move_file", "search_files", "get_file_info", "list_allowed_directories"] },
      ],
    },
    {
      title: "GitHub MCP Server",
      subtitle: "Runs in Docker; two fine-grained tokens keep the read-only and write demos apart",
      demo: MCP + "11_3_github_mcp_readonly_client.py, 11_4_github_mcp_write_client.py",
      split: [1, 1.1],
      left: [
        { type: "code", caption: ".env", code:
`GITHUB_READONLY_TOKEN=github_pat_...
GITHUB_WRITE_TOKEN=github_pat_...
GITHUB_DEMO_OWNER=<your user>
GITHUB_DEMO_REPO=mcp-demo-sandbox` },
        { type: "compare", size: 10, cols: [
          { title: "Read-only token", color: "navy", items: ["Repository access: Public repositories (read-only)"] },
          { title: "Write token", color: "coral", items: ["Only the sandbox repo; Contents + Issues: read & write"] },
        ] },
      ],
      right: [
        { type: "steps", size: 10, gap: 0.06, titleSize: 11, items: [
          { title: "Profile photo → Settings → Developer settings" },
          { title: "Personal access tokens → Fine-grained tokens" },
          { title: "Generate new token; name it, e.g. mcp-readonly-demo" },
          { title: "Short expiry – 7 to 30 days is plenty for a demo" },
          { title: "Choose the repository access shown on the left" },
          { title: "Generate, and copy it now – it is shown only once" },
        ] },
        { type: "text", size: 10.5, color: "slate", text: "Docker Desktop must be running." },
      ],
    },
    {
      title: "Managing a Repository from Claude Desktop",
      subtitle: "The same Docker image, registered in Claude Desktop – then you manage the repo in plain English",
      demo: "Claude Desktop  ·  config pattern from " + MCP + "11_3_github_mcp_readonly_client.py",
      split: [1.2, 1],
      left: [
        { type: "code", caption: "claude_desktop_config.json", code:
`{
  "mcpServers": {
    "github": {
      "command": "docker",
      "args": ["run", "-i", "--rm",
               "-e", "GITHUB_PERSONAL_ACCESS_TOKEN",
               "ghcr.io/github/github-mcp-server",
               "stdio", "--toolsets=repos,issues"],
      "env": {"GITHUB_PERSONAL_ACCESS_TOKEN":
              "github_pat_..."}
    }
  }
}` },
      ],
      right: [
        { type: "steps", size: 10.5, gap: 0.08, items: [
          { title: "Use the write token", text: "Scoped to the sandbox repo only" },
          { title: "Restart Claude Desktop", text: "The GitHub tools appear in the tools menu" },
          { title: "\"List the open issues in mcp-demo-sandbox\"", text: "Claude calls list_issues" },
          { title: "\"Add CHANGELOG.md, then open an issue\"", text: "Claude asks before each write tool" },
        ] },
        { type: "text", size: 10.5, color: "slate", text: "Add \"--read-only\" to the args for a browse-only setup." },
      ],
    },
    {
      title: "Playwright MCP Server",
      subtitle: "Browser automation as tools: open pages, click, fill forms, navigate, read what's on screen",
      demo: MCP + "11_5_playwright_mcp_gold_price_client.py, 11_6_playwright_mcp_login_demo_client.py",
      blocks: [
        { type: "compare", size: 11, cols: [
          { title: "11_5 – gold price", color: "navy", items: ["`browser_navigate` to goldprice.org", "`browser_wait_for`, then `browser_find` with a price pattern", "The price exists only as rendered page content – no API"] },
          { title: "11_6 – login demo", color: "teal", items: ["`browser_fill_form` on a public QA practice site", "`browser_click` to log in", "`browser_find` checks for success or the error message"] },
        ] },
        { type: "callout", eyebrow: "Why it matters", text: "Microsoft's official @playwright/mcp server (run with npx). Here the client calls the tools directly; give the same tools to an agent and it can use web UIs like a person." },
      ],
    },
    {
      title: "MCP Tools in LangChain and LangGraph",
      subtitle: "MultiServerMCPClient turns every server's tools into ordinary LangChain tools",
      demo: MCP + "11_7_langchain_…_tools.py, 11_7_2_…_flask.py, 11_8_langgraph_agent_mcp_tools.py",
      split: [1.25, 1],
      left: [
        { type: "code", caption: "11_8_langgraph_agent_mcp_tools.py (condensed)", code:
`client = MultiServerMCPClient({
    "crypto": {"transport": "stdio",
               "command": sys.executable,
               "args": [".../crypto_mcp_server.py"]},
    "forex":  {"transport": "stdio",
               "command": sys.executable,
               "args": [".../forex_mcp_server.py"]},
})

tools = await client.get_tools()
agent = create_react_agent(model=llm, tools=tools)
await agent.ainvoke({"messages": [{"role": "user",
    "content": "Price of ethereum in USD, and in INR?"}]})` },
      ],
      right: [
        { type: "steps", size: 10.5, items: [
          { title: "Two servers, one agent", text: "Crypto prices and exchange rates" },
          { title: "get_tools()", text: "Discovers and wraps every tool" },
          { title: "The agent chains them", text: "ETH in USD → USD to INR" },
          { title: "Same tools, two runtimes", text: "11_7 runs its own bind_tools loop; 11_8 a LangGraph ReAct agent; 11_7_2 adds a Flask UI" },
        ] },
      ],
    },
    {
      title: "MCP Tools in CrewAI",
      subtitle: "The same two servers, wrapped as CrewAI tools by a small hand-written bridge",
      demo: MCP + "11_9_crewai_mcp_tools.py",
      split: [1.25, 1],
      left: [
        { type: "code", caption: "11_9_crewai_mcp_tools.py (condensed)", code:
`def mcp_tool_to_crewai(script, mcp_tool) -> BaseTool:
    class MCPTool(BaseTool):
        name: str = mcp_tool.name
        description: str = mcp_tool.description
        args_schema = schema_to_model(mcp_tool.inputSchema)

        def _run(self, **kwargs) -> str:
            return asyncio.run(
                call_mcp_tool(script, mcp_tool.name, kwargs))
    return MCPTool()

analyst = Agent(role="Crypto Price Analyst",
                tools=load_tools(),   # all MCP tools
                llm="gpt-4o-mini", ...)
Crew(agents=[analyst], tasks=[task]).kickoff()` },
      ],
      right: [
        { type: "steps", size: 10.5, items: [
          { title: "list_tools() on each server", text: "Crypto prices and exchange rates" },
          { title: "One BaseTool per MCP tool", text: "Name, description and an args schema built from the JSON input schema" },
          { title: "_run() → call_tool()", text: "CrewAI calls tools synchronously, so the async MCP call runs in asyncio.run()" },
        ] },
        { type: "text", size: 10.5, color: "slate", text: "crewai-tools[mcp] ships the same bridge as MCPServerAdapter." },
      ],
    },
    {
      title: "A Two-Server Report Pipeline",
      subtitle: "Query a database through one MCP server, write the report through another – no LLM needed",
      demo: MCP + "11_10_sqlite_to_filesystem_report_pipeline.py",
      blocks: [
        { type: "flow", items: [
          { icon: "FaFileCsv", label: "Superstore CSV", caption: "A sample of real Kaggle orders, cleaned with pandas" },
          { icon: "FaDatabase", label: "SQLite MCP server", caption: "Four read_query aggregates: category, region, top products, yearly trend" },
          { icon: "FaGears", label: "The client script", caption: "Formats the results into a report", color: "coral" },
          { icon: "FaFolderOpen", label: "Filesystem MCP server", caption: "write_file into the sandboxed reports/ folder", color: "teal" },
        ] },
        { type: "callout", eyebrow: "The point", text: "The two servers never talk to each other – the client composes them. MCP is useful for plain orchestration too, not only for agents." },
      ],
    },
    {
      title: "MCP in Production",
      subtitle: "What changes when MCP servers serve real users",
      demo: MCP + "authentication/version_1 → version_2 → version_3",
      blocks: [
        { type: "tiles", cols: 3, items: [
          { icon: "FaSitemap", title: "One server or many", text: "Specialised servers are easier to secure and scale" },
          { icon: "FaScaleBalanced", title: "Load balancing", text: "Several instances behind one endpoint" },
          { icon: "FaDocker", title: "Containers", text: "Package each server as an image" },
          { icon: "FaDoorOpen", title: "API gateway", text: "One front door, rate limits, routing" },
          { icon: "FaKey", title: "Authentication", text: "OAuth2 tokens, not shared secrets" },
          { icon: "FaChartLine", title: "Monitoring and logging", text: "Every tool call recorded" },
        ] },
        { type: "text", size: 11, color: "slate", text: "The authentication folder steps a Tavily search server from no auth → a static bearer token → real OAuth2 tokens from Scalekit." },
      ],
    },
    {
      kind: "summary",
      title: "Module 11 Summary",
      subtitle: "What you built",
      built: [
        { tag: "11_1", title: "Database and files", text: "SQLite and filesystem servers from a client" },
        { tag: "11_3", title: "GitHub", text: "Read-only and write access with scoped tokens" },
        { tag: "11_5", title: "A browser", text: "Playwright reading prices and logging in" },
        { tag: "11_8", title: "Agents with MCP tools", text: "Crypto + forex servers in one ReAct agent" },
        { tag: "11_9", title: "A crew with MCP tools", text: "The same servers as CrewAI tools" },
      ],
      takeaways: [
        "Reuse official and community servers first",
        "Scope access: allowed roots, fine-grained tokens",
        "The client composes servers; servers stay independent",
        "MCP tools plug into LangChain, LangGraph and CrewAI",
        "Production needs gateways, auth and monitoring",
      ],
      next: "Module 12: Deep Agents – Reflection, Planning and Memory",
    },
  ],
};
