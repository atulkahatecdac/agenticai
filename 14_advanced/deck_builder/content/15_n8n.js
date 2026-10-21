const M = "15_n8n/";

module.exports = {
  section: "Module 15 – Agentic Workflows with n8n",
  slides: [
    {
      kind: "opener",
      eyebrow: "Module 15",
      title: "Agentic Workflows with n8n",
      subtitle: "Low-code workflow automation that hands the hard decisions to a LangGraph agent",
      goals: [
        { icon: "FaDiagramProject", title: "Understand n8n", text: "nodes, triggers and where AI fits" },
        { icon: "FaDocker", title: "Run n8n yourself", text: "cloud, Docker or npm – and Docker step by step" },
        { icon: "FaRobot", title: "Combine n8n with LangGraph", text: "n8n moves the data; the agent makes the call" },
        { icon: "FaPlug", title: "Reach a CRM through MCP", text: "Baserow's hosted MCP server as agent tools" },
      ],
      agenda: [
        "What n8n is",
        "Ways to run n8n",
        "Running n8n in Docker",
        "Insurance claim workflow: n8n + LangGraph",
        "Setting up Baserow and its MCP server",
        "How the agent talks to Baserow",
      ],
    },
    {
      title: "n8n",
      subtitle: "A workflow automation platform: connect apps, APIs and services with nodes – no-code or low-code",
      demo: "Concept",
      split: [1, 1.1],
      left: [
        { type: "icons", d: 0.38, size: 11, items: [
          { icon: "FaLink", title: "Connects everything", text: "Hundreds of app and API integrations" },
          { icon: "FaRepeat", title: "Automates repetitive work", text: "Triggered by emails, webhooks, schedules" },
          { icon: "FaCubes", title: "Built from nodes", text: "Each node does one step; data flows between them" },
          { icon: "FaRobot", title: "AI-ready", text: "LLM, agent and HTTP nodes call models and services" },
        ] },
      ],
      right: [
        { type: "tree", boxW: 1.5, size: 10, boxH: 0.34, gapY: 0.22, rows: [["New email"], ["Extract content"], [{ label: "AI model classifies", fill: "coral" }], [{ label: "Important → notify", fill: "teal" }, "Normal → archive"]] },
      ],
    },
    {
      title: "Ways to Run n8n",
      subtitle: "Same product, three places to run it",
      demo: "Concept",
      blocks: [
        { type: "table", size: 10.5, widths: [1.9, 1.7, 2.2, 1.5, 2.2], head: ["Option", "Runs on", "Installation", "Maintenance", "Best for"], rows: [
          ["n8n Cloud", "n8n's servers", "None", "n8n does it", "Beginners, quick start, production"],
          ["Self-hosted, Docker", "Your PC, server or VM", "Docker + the n8n container", "You", "Developers, labs, production"],
          ["Self-hosted, npm", "Your PC or server", "Node.js + the n8n package", "You", "Learning, customisation"],
        ] },
      ],
    },
    {
      title: "Running n8n in Docker",
      subtitle: "One volume for n8n's data, one folder shared with the container for files",
      demo: "Terminal: docker run … docker.n8n.io/n8nio/n8n  →  http://localhost:5678",
      split: [1.35, 1],
      left: [
        { type: "code", caption: "Install Docker, then", code:
`docker volume create n8n_data

docker run -it --rm --name n8n -p 5678:5678 ^
  -e GENERIC_TIMEZONE="Asia/Calcutta" -e TZ="Asia/Calcutta" ^
  -e N8N_ENFORCE_SETTINGS_FILE_PERMISSIONS=true ^
  -v n8n_data:/home/node/.n8n ^
  -v C:/Users/<you>/myfiles:/home/node/.n8n-files ^
  docker.n8n.io/n8nio/n8n` },
      ],
      right: [
        { type: "steps", size: 10.5, items: [
          { title: "Open localhost:5678" },
          { title: "Create the owner account", text: "Any email, name and password – it stays local" },
          { title: "Get the free licence key", text: "Ask for it on the next screen; it arrives by email" },
          { title: "Activate it", text: "Usage and plan → paste the key" },
        ] },
      ],
    },
    { kind: "image", src: "n8n_claim_workflow.png", alt: "Automated insurance claim processing: n8n, Baserow and LangGraph", demo: M + "14_1_n8n_langgraph.json + " + M + "1_claim_analysis_agent.py" },
    {
      title: "n8n with LangGraph: Setup",
      subtitle: "n8n handles email, files and the CRM rows; the LangGraph agent decides the claim",
      demo: M + "1_claim_analysis_agent.py  (http://localhost:8020/docs)",
      split: [1, 1.1],
      left: [
        { type: "steps", size: 10.5, gap: 0.1, items: [
          { title: "Create a Baserow account", text: "Tables: customers, policy, claims" },
          { title: "Create its MCP endpoint", text: "My settings → MCP server → Create endpoint" },
          { title: "Put the URL in .env", text: "`BASEROW_MCP_URL=…` – treat it like a password" },
          { title: "Start the agent first", text: "Run `1_claim_analysis_agent.py` – it serves port 8020" },
          { title: "Then import and run the workflow", text: "`14_1_n8n_langgraph.json` in n8n" },
        ] },
      ],
      right: [
        { type: "text", text: "**The agent graph**", size: 12 },
        { type: "chain", size: 10, items: ["receive_claim", "lookup_claim", "check_policy", "analyze_documents", "update_accident_date", "decision"], highlight: [1, 2, 4] },
        { type: "callout", eyebrow: "Nothing mocked", text: "lookup, policy check and update each run a small ReAct agent whose tools come from Baserow's MCP server." },
      ],
    },
    { kind: "image", src: "langgraph_baserow_mcp.png", alt: "LangGraph reaches Baserow through MCP – without writing an MCP client", demo: M + "1_claim_analysis_agent.py" },
    {
      kind: "summary",
      title: "Module 15 Summary",
      subtitle: "What you built",
      built: [
        { tag: "n8n", title: "n8n in Docker", text: "A local, licensed n8n instance" },
        { tag: "flow", title: "A claim workflow", text: "Email in, CRM rows created, documents passed on" },
        { tag: "agent", title: "A LangGraph claim agent", text: "Served over HTTP for n8n to call" },
        { tag: "MCP", title: "CRM through MCP", text: "Baserow's hosted server as agent tools" },
      ],
      takeaways: [
        "Let n8n move data; let agents make decisions",
        "Expose agents over HTTP so any workflow can call them",
        "Hosted MCP servers turn SaaS apps into agent tools",
        "Treat MCP endpoint URLs as secrets",
        "Start the agent before triggering the workflow",
      ],
      next: "Module 16: Guardrails – NeMo, Guardrails AI and Safety",
    },
  ],
};
