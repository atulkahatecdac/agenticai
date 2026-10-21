const MCP = "../6_mcp/";

module.exports = {
  section: "Module 10 – Model Context Protocol",
  slides: [
    {
      kind: "opener",
      eyebrow: "Module 10",
      title: "Model Context Protocol (MCP)",
      subtitle: "One open standard for connecting AI apps to tools, data and prompts – write a server once, use it anywhere",
      goals: [
        { icon: "FaPlug", title: "Explain hosts, clients and servers", text: "and why a standard protocol helps" },
        { icon: "FaShapes", title: "Use the three primitives", text: "resources, tools and prompts" },
        { icon: "FaRightLeft", title: "Follow the messages", text: "JSON-RPC, stdio vs streamable HTTP, initialise, discover" },
        { icon: "FaShieldHalved", title: "Secure a server", text: "scopes, access control, input validation" },
      ],
      agenda: [
        "What MCP is: host, client, server",
        "Writing a server with FastMCP",
        "Primitives: resources, tools, prompts",
        "Prompts are not tools",
        "Message format and transports",
        "Initialisation and tool discovery",
        "Prompt templates as a primitive",
        "Security and input validation",
      ],
    },
    {
      title: "What Is MCP?",
      subtitle: "An open standard that lets AI apps talk to external tools, data sources and APIs in a structured, secure, consistent way",
      demo: "Concept",
      split: [1, 1.1],
      left: [
        { type: "text", text: "**One host, one client per server**", size: 11.5 },
        { type: "chain", size: 10, items: ["Host", "Client", "Server A", "Files / DB"], highlight: [0] },
        { type: "chain", size: 10, gapBefore: 0.12, items: ["Host", "Client", "Server B", "Service"], highlight: [0] },
        { type: "chain", size: 10, gapBefore: 0.12, items: ["Host", "Client", "Server C", "Web API"], highlight: [0] },
      ],
      right: [
        { type: "table", size: 10, widths: [1.3, 3.0], head: ["Component", "Meaning"], rows: [
          ["Host", "The app that uses MCP: Claude Desktop, an IDE, your own agent"],
          ["Client", "Built into the host; one 1:1 connection per server"],
          ["Server", "Exposes capabilities through the standard protocol"],
          ["Local resources", "Files, databases and services on this computer"],
          ["Remote services", "Internet APIs that a server calls for you"],
        ] },
      ],
    },
    {
      title: "A Server in a Few Lines",
      subtitle: "FastMCP turns decorated Python functions into MCP tools – the docstring becomes the description",
      demo: MCP + "6_1_weather_mcp_server.py, 6_1_weather_mcp_client.py",
      split: [1.15, 1],
      left: [
        { type: "code", caption: "6_1_weather_mcp_server.py", code:
`from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Weather")

@mcp.tool()
def get_weather(location: str) -> str:
    """Gets the weather given a location.
    location: city, country, state, etc."""
    return "The weather is hot and dry"

if __name__ == "__main__":
    mcp.run()          # stdio by default` },
      ],
      right: [
        { type: "code", caption: "MCP SDK 1.x", code: `from mcp.server.fastmcp import FastMCP
mcp = FastMCP("Forex")` },
        { type: "code", caption: "MCP SDK 2.x", code: `from mcp.server.mcpserver import MCPServer
mcp = MCPServer("Forex")` },
        { type: "text", size: 11, color: "slate", text: "The repo's servers use the 1.x import; the 2.x SDK renames the class." },
      ],
    },
    {
      title: "Three Primitives",
      subtitle: "Every MCP server exposes one or more of these",
      demo: "Concept",
      blocks: [
        { type: "cards", size: 10.5, items: [
          { icon: "FaFileLines", title: "Resource", tag: "Read", lines: ["Information the AI can read – passive data, no action", "**e.g.** a file, PDF, DB record, API response", "`forex://rates/USD-INR/latest`"] },
          { icon: "FaScrewdriverWrench", title: "Tool", tag: "Act", lines: ["An action or computation the AI decides to call", "**e.g.** search the web, send email, query a DB, book a flight", "`place_order(pair, amount, type)`"] },
          { icon: "FaComment", title: "Prompt", tag: "Guide", lines: ["A reusable instruction template the user picks", "**e.g.** summarise a document, review code, write minutes", "`/analyze-currency-trend`"] },
        ] },
        { type: "callout", eyebrow: "Example", text: "\"Should I convert my USD to INR now – and if so, do it for $1,000?\" The AI reads the rate resources, runs the trend-analysis prompt, then calls the place_order tool." },
      ],
    },
    {
      title: "Prompts Are Not Tools",
      subtitle: "A prompt is something the user chooses; a tool is something the AI chooses",
      demo: "Concept",
      split: [1.2, 1],
      left: [
        { type: "steps", size: 10.5, gap: 0.1, items: [
          { title: "The user types / in a chat app connected to a forex server", text: "A menu shows /analyze-currency-trend and /convert-currency" },
          { title: "They pick /analyze-currency-trend", text: "The server fills in: \"Fetch the last 30 days of USD/INR, compute volatility, say if the trend is bullish or bearish\"" },
          { title: "They press Send" },
          { title: "Behind the scenes the AI calls a tool", text: "`get_exchange_rate_history(pair=\"USD/INR\", days=30)`" },
        ] },
      ],
      right: [
        { type: "compare", size: 10.5, cols: [
          { title: "Prompt", color: "coral", items: ["Pre-written question", "Picked by the user from a menu"] },
          { title: "Tool", color: "teal", items: ["Code", "Called by the AI on its own"] },
        ] },
      ],
    },
    {
      title: "How MCP Messages Travel",
      subtitle: "Format = what a message looks like.  Transport = how it gets delivered.",
      demo: "Concept",
      split: [1, 1.1],
      left: [
        { type: "icons", d: 0.38, size: 11, items: [
          { icon: "FaCode", title: "JSON-RPC 2.0", text: "The grammar of every request, result and error" },
          { icon: "FaTerminal", title: "stdio", text: "Client and server on the same machine; the server runs as a subprocess. Simple, fast, no network" },
          { icon: "FaGlobe", title: "Streamable HTTP", text: "For remote, hosted servers – works over the network" },
        ] },
      ],
      right: [
        { type: "code", caption: "Request (client → server)", code:
`{"jsonrpc": "2.0", "id": 1,
 "method": "tools/call",
 "params": {"name": "get_weather",
            "arguments": {"city": "Paris"}}}` },
        { type: "code", caption: "Response (server → client)", code:
`{"jsonrpc": "2.0", "id": 1,
 "result": {"temperature": 20, "unit": "C"}}` },
        { type: "text", size: 10.5, color: "slate", text: "The LLM then answers: \"The current temperature in Paris is 20°C.\"" },
      ],
    },
    {
      title: "Initialisation and Tool Discovery",
      subtitle: "Before any tool call, client and server say what they support; then the client asks what tools exist",
      demo: MCP + "6_0_database_mcp_client_discover_methods.py",
      split: [1.1, 1],
      left: [
        { type: "text", text: "**Step 1 – session initialisation** (trading app ↔ forex server)", size: 11.5 },
        { type: "steps", size: 10.5, gap: 0.08, items: [
          { title: "initialize request →", text: "Client capabilities: roots, sampling" },
          { title: "← initialize response", text: "Server capabilities – tools: get_rates, convert; resources: forex://rates; prompts: fx_analysis" },
          { title: "initialized notification →", text: "A simple ack – the session is ready" },
        ] },
        { type: "text", size: 10.5, color: "slate", text: "Client capabilities describe what the app can do for the server – not a choice of tools." },
      ],
      right: [
        { type: "text", text: "**Step 2 – tool discovery**", size: 11.5 },
        { type: "code", caption: "The server defines a tool…", code:
`@mcp.tool()
def search_documents(query: str,
                     limit: int = 5) -> list:
    """Search company documents by keyword."""` },
        { type: "code", caption: "…the client lists it with its schema", code:
`search_documents
├── query: string
└── limit: integer` },
        { type: "text", size: 10.5, color: "slate", text: "The LLM reads these schemas to decide whether to call a tool." },
      ],
    },
    {
      title: "Prompt Templates as a Primitive",
      subtitle: "Reviewed wording lives on the server, so every client – web app, Slack bot, CLI – says it the same way",
      demo: MCP + "6_11_prompt_template_mcp_server.py, 6_11_prompt_template_mcp_client.py",
      split: [1.2, 1],
      left: [
        { type: "code", caption: "6_11_prompt_template_mcp_server.py (condensed)", code:
`mcp = FastMCP("SupportPrompts")

@mcp.tool()
def get_product_info(product_name: str) -> str:
    """Look up a product's details by name."""
    ...                     # SQLite product catalogue

@mcp.prompt()
def answer_product_question(product_name: str,
        product_details: str, customer_question: str) -> str:
    """Answer a product question from catalogue data"""
    return f"""A customer asked ... {customer_question}"""

@mcp.prompt()
def product_not_found_reply(product_name, customer_question): ...` },
      ],
      right: [
        { type: "chain", size: 10, items: ["Tool: real data", "Prompt: approved wording", "LLM answer"], highlight: [1] },
        { type: "callout", eyebrow: "Division of labour", text: "Prompts guide the LLM; tools reach external systems. Together the answer is grounded and consistently phrased." },
      ],
    },
    {
      title: "Securing an MCP Server",
      subtitle: "Never trust a request just because it came from an AI client",
      demo: MCP + "6_12_sql_injection_mcp_server.py  ·  " + MCP + "6_10_malicious_mcp_server.py",
      split: [1, 1.1],
      left: [
        { type: "icons", d: 0.38, size: 11, items: [
          { icon: "FaKey", title: "Permission scopes", text: "Read files, search documents, run SQL, send email – grant only what's needed" },
          { icon: "FaUserLock", title: "Access control", text: "Allow or deny each request – e.g. read but not write" },
          { icon: "FaFilter", title: "Validate, sanitise, authorise", text: "Every argument, every time – against mistakes, malformed input and attacks" },
        ] },
      ],
      right: [
        { type: "compare", size: 10.5, cols: [
          { title: "6_12 – SQL injection", color: "navy", items: ["A tool that builds SQL from model input", "Shows the attack, then the validated version"] },
          { title: "6_10 – malicious server", color: "coral", items: ["A \"harmless calculator\" that also writes a file to your home folder", "Review server code before you connect – awareness demo, never a template"] },
        ] },
        { type: "callout", eyebrow: "Rule", text: "Treat tool arguments as untrusted user input – parameterised queries, allow-lists, least privilege." },
      ],
    },
    {
      kind: "summary",
      title: "Module 10 Summary",
      subtitle: "What you built",
      built: [
        { tag: "6_1", title: "A first MCP server", text: "One FastMCP tool, called from a client" },
        { tag: "6_0", title: "Discovery", text: "Listing a server's tools and schemas" },
        { tag: "6_11", title: "Prompt templates", text: "Server-owned wording plus a grounding tool" },
        { tag: "6_12", title: "A hardened server", text: "Input validation against SQL injection" },
      ],
      takeaways: [
        "MCP standardises how apps reach tools and data",
        "Resources are read, tools act, prompts guide",
        "JSON-RPC everywhere; stdio locally, HTTP remotely",
        "The LLM chooses tools from their schemas – describe them well",
        "Validate every tool argument on the server",
      ],
      next: "Module 11: MCP Ecosystem Integrations",
    },
  ],
};
