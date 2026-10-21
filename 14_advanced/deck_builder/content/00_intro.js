module.exports = {
  section: "Introduction",
  slides: [
    {
      kind: "cover",
      eyebrow: "Advanced Engineering",
      title: "Agentic AI",
      description: "Nineteen modules: from a clean Python setup and your first LLM call to stateful agents, MCP, guardrails, monitoring and Docker deployment.",
      author: "Atul Kahate",
      authorLink: "linkedin.com/in/atulkahate",
      repo: "github.com/atulkahatecdac/agenticai",
      footnote: "Modules 01–19  ·  Demo code: 14_advanced/<module folder>",
      journey: [
        { icon: "FaPython", title: "Foundations", text: "Python tooling, APIs, LLMs and prompting" },
        { icon: "FaDatabase", title: "Retrieval and LangChain", text: "Embeddings, vector stores, RAG, tools" },
        { icon: "FaDiagramProject", title: "LangGraph and LangSmith", text: "Stateful graphs, persistence, evaluation" },
        { icon: "FaPlug", title: "MCP, deep agents, crews", text: "Standard tools, reflection, multi-agent teams" },
        { icon: "FaShieldHalved", title: "Production", text: "Guardrails, monitoring, fine-tuning, Docker" },
      ],
    },
    {
      title: "Course Map",
      subtitle: "Each module has its own demo folder in 14_advanced – the DEMO bar on every slide names the script",
      top: true,
      blocks: [
        { type: "cols", gap: 0.25, cols: [
          [{ type: "table", size: 9.5, widths: [0.4, 1.95, 1.95], head: ["#", "Module", "Focus"], rows: [
            ["01", "Python and dev environment", "venv, uv, .env, asyncio"],
            ["02", "FastAPI, Streamlit, Gradio", "Serving AI apps"],
            ["03", "LLM fundamentals & prompting", "Tokens, APIs, prompts"],
            ["04", "Embeddings & vector databases", "Chroma, FAISS, hybrid"],
            ["05", "LangChain core", "LCEL, memory, RAG, retrievers"],
            ["06", "LangChain agents & tools", "Tools, ReAct, SQL agents"],
            ["07", "LangGraph", "State, nodes, routing"],
            ["08", "Cycles, HITL, persistence", "Loops, HITL, checkpoints"],
            ["09", "LangSmith", "Tracing and evaluation"],
            ["10", "Model Context Protocol", "Primitives, transports"],
          ] }],
          [{ type: "table", size: 9.5, widths: [0.4, 1.95, 1.95], head: ["#", "Module", "Focus"], rows: [
            ["11", "MCP ecosystem", "Ready-made MCP servers"],
            ["12", "Deep agents", "Reflection, planning, memory"],
            ["13", "CrewAI", "Crews, flows, managers"],
            ["14", "Agentic RAG & GraphRAG", "Self-RAG, CRAG, RAGAS"],
            ["15", "Agentic workflows with n8n", "n8n + LangGraph + MCP"],
            ["16", "Guardrails", "NeMo, Presidio, red-teaming"],
            ["17", "Monitoring & fine-tuning", "OTel, Prometheus, LoRA"],
            ["18", "Docker & deployment", "Images, Compose, blue/green"],
            ["19", "Capstone projects", "Three end-to-end apps"],
          ] }],
        ] },
      ],
    },
  ],
};
