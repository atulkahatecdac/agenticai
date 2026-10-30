module.exports = {
  section: "Introduction",
  slides: [
    {
      kind: "cover",
      eyebrow: "PGP Program",
      title: "Agentic AI",
      description: "Nine hands-on sessions: from your first OpenAI agent to stateful LangGraph workflows, multi-agent crews, agentic RAG and deep agents.",
      author: "Atul Kahate",
      authorLink: "linkedin.com/in/atulkahate",
      repo: "github.com/atulkahatecdac/agenticai",
      footnote: "Sessions 1–9  ·  Demo code: 16_PGP-Agentic/code/session_N",
      journey: [
        { icon: "FaRobot", title: "OpenAI Agents SDK", text: "First agents, tools and design patterns" },
        { icon: "FaLink", title: "LangChain", text: "Chains, memory, RAG and tool-using agents" },
        { icon: "FaDiagramProject", title: "LangGraph", text: "Stateful graphs, loops, human-in-the-loop" },
        { icon: "FaPeopleGroup", title: "CrewAI and AutoGen", text: "Multi-agent crews, flows and teams" },
        { icon: "FaBrain", title: "Agentic RAG and deep agents", text: "Smarter retrieval, reflection, memory" },
      ],
    },
    {
      kind: "map",
      title: "Course Map",
      subtitle: "Nine sessions, each with live demos from the course repository",
      rows: [
        { title: "Agentic AI Foundations and Agent Architectures", focus: "OpenAI Agents SDK, tools, design patterns" },
        { title: "LangChain Core: Chains, Memory and RAG", focus: "LCEL, memory, vector stores, RAG pipeline" },
        { title: "LangChain Agents and Tool Use", focus: "Prompting, custom tools, SQL agents, tool chaining" },
        { title: "LangGraph: Stateful Workflows and Routing", focus: "State, nodes, edges, streaming, LangGraph Studio" },
        { title: "LangGraph: Cycles, HITL and Persistence", focus: "Loops, human approval, checkpointers, guardrails" },
        { title: "Multi-Agent Orchestration with CrewAI", focus: "Crews, flows, managers, memory, observability" },
        { title: "Multi-Agent Systems with Microsoft AutoGen", focus: "AgentChat, teams, GraphFlow, memory" },
        { title: "Agentic RAG and GraphRAG for Agents", focus: "Self-RAG, CRAG, reranking, GraphRAG, RAGAS" },
        { title: "Deep Agents: Reflection, Planning and Memory", focus: "Reflection, replanning, long-term memory" },
      ],
    },
  ],
};
