const M = "19_capstone/";
const W = M + "warranty_returns/";

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
        "Part 2: tests, load, security audit, deployment",
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
      title: "Capstone Part 2: Prove It, Then Ship It",
      subtitle: "Part 1 works on a laptop. Part 2 shows it works, is safe and is fast enough – then deploys it",
      demo: W + "README.md  →  Part 2",
      blocks: [
        { type: "table", size: 10, widths: [2.4, 4.2, 1.6], head: ["Step", "What it proves", "Verified"], rows: [
          ["19_10_integration_tests.py", "API + graph + checkpoints + approval gate + guardrails + auth + metrics, together", "10 passed"],
          ["19_11_load_test.py", "p50/p95/p99, tickets per minute, errors and cost per ticket under 10 concurrent customers", "0 errors, p95 ≈ 9 s"],
          ["19_12_security_audit.py", "Injection, PII, access control, SQL injection, data exfiltration, exposure", "8 pass, 4 warn, 0 fail"],
          ["deploy/", "One image for API and UI; Compose with Prometheus and Grafana; a CI/CD pipeline", "Stack up, healthy"],
          ["docs/", "Architecture decision records and the OpenAPI spec", "3 ADRs, 7 paths"],
        ] },
        { type: "callout", eyebrow: "Why bother", text: "These steps found three real bugs in a system that already passed its 20-ticket scorecard – next slides." },
      ],
    },
    {
      title: "Tests That Found Real Bugs",
      subtitle: "Integration tests check the system; a load test and a restart test check it under real conditions",
      demo: W + "19_10_integration_tests.py  ·  19_11_load_test.py --users 10",
      split: [1, 1.05],
      left: [
        { type: "code", caption: "19_10 – one of ten tests", code:
`def test_paused_ticket_survives_an_api_restart(
        client):
    t = submit(client, "...ZenBook... refund.")
    assert t["status"] == "waiting_approval"
    api.TICKETS.clear()      # what a restart does
    assert api._recover_waiting_tickets() >= 1
    r = client.post(f"/tickets/{t['id']}/approve",
                    ...)
    assert r.status_code == 200` },
        { type: "table", size: 9.5, widths: [1.9, 0.6, 0.6, 0.6], head: ["19_11, 10 customers", "p50", "p95", "p99"], rows: [
          ["Ticket resolved (s)", "7.0", "8.8", "9.5"],
        ] },
        { type: "text", size: 10, color: "slate", text: "About 90 tickets a minute, 0 errors, offline mode." },
      ],
      right: [
        { type: "steps", size: 10.5, gap: 0.08, items: [
          { title: "Restart lost paused tickets", text: "`docker restart` → \"Unknown ticket\": the checkpoint survived, the API's in-memory list did not. Fix: rebuild it from the checkpoints at startup" },
          { title: "Concurrent tickets crashed Chroma", text: "\"Could not connect to tenant\" – a new client per call raced. Fix: one shared client behind a lock" },
          { title: "1 s alone, ~7 s with 10 at once", text: "Not a bug – one process does all the work. Scale-out needs shared checkpoints (ADR 0003)" },
        ] },
      ],
    },
    {
      title: "The Security Audit",
      subtitle: "Attack the running system the way an outsider would; FAIL blocks the release, WARN is a decision to record",
      demo: W + "19_12_security_audit.py  (exit code 1 on any FAIL)",
      split: [1.05, 1],
      left: [
        { type: "table", size: 9.5, widths: [2.4, 0.7], head: ["Check", "Result"], rows: [
          ["Prompt injection: no refund without approval (5 attacks)", "PASS"],
          ["System prompt not revealed", "PASS"],
          ["PII scrubbed before storage; not echoed", "PASS"],
          ["Approvals need authentication", "PASS*"],
          ["Oversized input rejected (20,000 chars → 422)", "PASS"],
          ["SQL injection has no effect (15 → 15 orders)", "PASS"],
          ["No bulk data disclosure", "PASS"],
          ["Docs, /metrics, rate limit, default approver key", "WARN"],
        ] },
      ],
      right: [
        { type: "callout", eyebrow: "* Found by this audit", text: "Before Part 2, anyone who could reach the API could approve a ₹65,000 refund: /approve had no authentication." },
        { type: "code", caption: "The fix in 19_7_api.py", code:
`def require_approver(
        x_approver_key: str | None = Header(None)):
    if x_approver_key != APPROVER_KEY:
        raise HTTPException(401, "Approver key ...")

@app.post("/tickets/{ticket_id}/approve",
    dependencies=[Depends(require_approver)])` },
        { type: "text", size: 10.5, color: "slate", text: "A shared key is a stop-gap: production puts approvers behind SSO and records who approved (ADR 0002)." },
      ],
    },
    {
      title: "Containers, a Gated Pipeline, Decision Records",
      subtitle: "The same system as four containers; a release only goes out if every check passes",
      demo: W + "deploy/  ·  docker compose -f deploy/docker-compose.yml up -d --build",
      split: [1, 1.1],
      left: [
        { type: "table", size: 10, widths: [1.1, 2.6], head: ["Service", "Port · role"], rows: [
          ["api", "8019 · same image, python 19_7_api.py"],
          ["ui", "8519 · same image, streamlit run 19_8"],
          ["prometheus", "9096 · scrapes api:8019 by service name"],
          ["grafana", "3001 · the Part 1 dashboard, provisioned"],
        ] },
        { type: "text", size: 10.5, color: "slate", text: "A named volume over data/ keeps the checkpoints, so a ticket waiting for approval was still waiting after `docker restart` – and could be approved." },
      ],
      right: [
        { type: "text", size: 11, text: "**deploy/ci-cd.yml – every gate offline, free and repeatable**" },
        { type: "chain", size: 9.5, items: ["19_10 tests", "19_9 scorecard 20/20", "19_12 audit", "19_11 SLO", "build + push", "approve", "Cloud Run"], highlight: [5] },
        { type: "table", size: 9.5, widths: [0.5, 3.2], head: ["ADR", "Decision"], rows: [
          ["0001", "Refund decisions by rules, not the LLM"],
          ["0002", "Humans approve big refunds; only approvers can"],
          ["0003", "SQLite checkpoints, one instance – until scale-out"],
        ] },
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
