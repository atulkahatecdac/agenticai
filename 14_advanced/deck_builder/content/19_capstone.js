const M = "19_capstone/";

module.exports = {
  section: "Module 19 – Capstone Projects",
  slides: [
    {
      kind: "opener",
      eyebrow: "Module 19",
      title: "Capstone Projects",
      subtitle: "Three end-to-end applications that combine the course – each with its own README, slides and demo guide",
      goals: [
        { icon: "FaShieldHalved", title: "Insurance assistant", text: "Foundation: OpenAI Agents SDK, tools, RAG, MCP, HITL" },
        { icon: "FaLaptopCode", title: "IT helpdesk copilot", text: "Intermediate: fully local, LangGraph multi-agent" },
        { icon: "FaBoxOpen", title: "Warranty & returns assistant", text: "Advanced: hybrid RAG, MCP, FastAPI, monitoring" },
        { icon: "FaRoute", title: "Pick one and extend it", text: "every step is a separate, runnable script" },
      ],
      agenda: [
        "The three projects at a glance",
        "SecureLife Insurance Policy Assistant",
        "BrightPath IT Helpdesk Copilot",
        "ElectroMart Warranty & Returns Assistant",
        "How to run them side by side",
      ],
    },
    {
      title: "Three Capstones at a Glance",
      subtitle: "Run every command from inside the project's folder, with the repo's .venv active",
      demo: M + "README.md",
      blocks: [
        { type: "table", size: 10, widths: [2.1, 1.1, 3.6, 1.7], head: ["Project", "Track", "Stack", "Ports"], rows: [
          ["insurance_assistant – SecureLife policy assistant", "Foundation", "OpenAI Agents SDK: tools, RAG (ChromaDB), structured output, MCP, guardrails, HITL, Flask", "API 8020, app 5020"],
          ["it_helpdesk – BrightPath IT copilot", "Intermediate", "Fully local: Ollama + LangChain/LangGraph multi-agent, RAG, 2 MCP servers, guardrails, HITL, SQLite, Flask, LLM-as-judge", "app 5021"],
          ["warranty_returns – ElectroMart assistant", "Advanced", "LangGraph multi-agent, ChromaDB hybrid RAG, MCP, FastAPI + Streamlit, Prometheus/Grafana, OpenAI or offline", "API 8019, Prometheus 9096, Grafana 3001"],
        ] },
        { type: "callout", eyebrow: "Designed to coexist", text: "Ports are chosen so all three can run at the same time." },
      ],
    },
    {
      title: "SecureLife Insurance Policy Assistant",
      subtitle: "\"What is the coverage amount in my health insurance policy?\" – answered from SQL, documents and an API",
      demo: M + "insurance_assistant/  (1_generate_data.py → 10_app_flask.py)",
      split: [1, 1.15],
      left: [
        { type: "steps", size: 10.5, gap: 0.08, items: [
          { title: "Find the customer's policies", text: "A read-only SQL tool – the customer comes from the session" },
          { title: "Read the wording when a rule is needed", text: "RAG over policy PDFs, filtered to health" },
          { title: "Call the Insurance API", text: "The LLM fills a Pydantic request; validation stops bad calls" },
          { title: "Answer", text: "\"Your coverage is ₹5,00,000, active till 31 Dec 2027.\"" },
        ] },
      ],
      right: [
        { type: "chain", size: 9.5, items: ["2 plain chatbot", "3 SQL tool", "4 RAG", "5 API + structured output", "6 one agent, 3 tools", "7 MCP", "8 guardrails", "9 HITL claim", "10 Flask app"], highlight: [5, 8] },
        { type: "text", size: 10.5, color: "slate", text: "One concept per step. `run_demo_questions.py` checks 14 questions end to end." },
      ],
    },
    {
      title: "BrightPath IT Helpdesk Copilot",
      subtitle: "Employees describe a problem; a team of local agents troubleshoots, unlocks, grants access or escalates",
      demo: M + "it_helpdesk/  (Ollama: qwen3:8b + nomic-embed-text, no API keys)",
      split: [1, 1.1],
      left: [
        { type: "table", size: 9.5, widths: [1.8, 2.2], head: ["Concept", "Where"], rows: [
          ["RAG over runbooks, with citations", "1_ingest_kb, 2_rag_kb_assistant"],
          ["MCP servers: helpdesk + identity", "3_…, 4_…"],
          ["Tool-calling ReAct agent", "5_tool_agent"],
          ["Guardrails (LLM classifiers)", "6_guardrails"],
          ["Multi-agent graph + HITL", "7_helpdesk_graph"],
          ["UI: employee + manager queue", "8_app_flask"],
          ["Evaluation, LLM-as-judge", "9_run_test_requests"],
        ] },
      ],
      right: [
        { type: "text", text: "**The data forces RAG and live tools together**", size: 11.5 },
        { type: "bullets", size: 10.5, items: [
          "VPN is degraded – the right answer is \"switch to Mumbai\", not a ticket",
          "Jira is down for everyone – say so; don't file a duplicate",
          "A contractor asks for AWS Production – policy says no",
          "Tableau is restricted – the manager must approve",
        ] },
      ],
    },
    {
      title: "ElectroMart Warranty & Returns Assistant",
      subtitle: "\"My headphones stopped charging after 5 months – I want a refund\" → a cited decision and a drafted reply",
      demo: M + "warranty_returns/  (19_1_generate_sample_data.py → 19_9_run_test_tickets.py)",
      blocks: [
        { type: "chain", size: 10, items: ["triage", "research ∥ investigate", "decide", "write ⇄ review", "validate", "approval gate"], highlight: [2, 5] },
        { type: "cols", cols: [
          [{ type: "bullets", size: 10.5, items: [
            "Hybrid RAG over 37 policy clauses (embeddings + BM25, RRF)",
            "MCP servers for orders and approval notifications",
            "Presidio PII scrubbing, input rails, output validators",
            "FastAPI with SSE, a Streamlit UI, Prometheus + Grafana",
          ] }],
          [{ type: "callout", eyebrow: "The design choice", text: "The refund decision is never made by the LLM: rules are applied to the retrieved clauses and order facts, so money decisions are repeatable. The LLM does the language work." }],
        ] },
        { type: "text", size: 10.5, color: "slate", text: "High-value refunds and every rejection go to a human approver. Runs with OpenAI or fully offline (`--offline`)." },
      ],
    },
    {
      kind: "summary",
      title: "Course Summary",
      subtitle: "From a Python environment to production agents",
      built: [
        { tag: "01–04", title: "Foundations", text: "Python tooling, APIs, LLMs, prompting, embeddings" },
        { tag: "05–09", title: "Frameworks", text: "LangChain, LangGraph, LangSmith" },
        { tag: "10–15", title: "Agent systems", text: "MCP, deep agents, CrewAI, agentic RAG, n8n" },
        { tag: "16–18", title: "Production", text: "Guardrails, monitoring, fine-tuning, Docker" },
        { tag: "19", title: "Capstones", text: "Three complete applications" },
      ],
      takeaways: [
        "Start simple: an LLM, a tool, a loop",
        "Add state, memory and retrieval only when needed",
        "Standardise tool access with MCP",
        "Measure everything – traces, metrics, evaluations",
        "Guard inputs, outputs and actions; keep humans in the loop",
      ],
      next: "Thank you! Keep building – the code is at github.com/atulkahatecdac/agenticai",
    },
  ],
};
