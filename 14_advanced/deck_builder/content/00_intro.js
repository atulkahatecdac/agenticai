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
    {
      title: "Software 1.0 → 2.0 → 3.0",
      subtitle: "Andrej Karpathy: how we program computers has changed twice",
      demo: "Concept",
      blocks: [
        { type: "flow", d: 0.8, labelSize: 14, size: 11, items: [
          { icon: "FaCode", label: "Software 1.0", caption: "Humans write code" },
          { icon: "FaBrain", label: "Software 2.0", caption: "Networks learn weights from data" },
          { icon: "FaComments", label: "Software 3.0", caption: "Prompts in English program an LLM" },
        ] },
        { type: "cards", titleSize: 13, codeSize: 9.5, items: [
          { n: "1", color: "navy", title: "The program is code", code:
`if "great" in review:
    return "positive"
if "awful" in review:
    return "negative"` },
          { n: "2", color: "coral", title: "The program is weights", code:
`model.fit(reviews, labels)
model.predict(review)` },
          { n: "3", color: "teal", title: "The program is a prompt", code:
`Is this review positive
or negative?
{review}` },
        ] },
      ],
    },
    { kind: "image", full: true, src: "software_1_2_3.png", alt: "Software 1.0 → 2.0 → 3.0: the evolution of programming" },
    { kind: "image", full: true, src: "ml_to_agentic_ai.png", alt: "From ML to Agentic AI – key terms with a travel-planning example" },
    { kind: "image", full: true, src: "llm_landscape_pricing.png", alt: "The LLM landscape – models and API pricing" },
  ],
};
