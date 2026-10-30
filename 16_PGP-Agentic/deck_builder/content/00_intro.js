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
      footnote: "Sessions 1–9  ·  08:00–11:00 AM  ·  Demo code: 16_PGP-Agentic/code/session_N",
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
      subtitle: "Nine sessions, each 08:00–11:00 AM, each with live demos from the course repository",
      rows: [
        { date: "Sat 24-Oct", title: "Agentic AI Foundations and Agent Architectures", focus: "OpenAI Agents SDK, tools, design patterns" },
        { date: "Sat 25-Oct", title: "LangChain Core: Chains, Memory and RAG", focus: "LCEL, memory, vector stores, RAG pipeline" },
        { date: "Sun 31-Oct", title: "LangChain Agents and Tool Use", focus: "Prompting, custom tools, SQL agents, tool chaining" },
        { date: "Sat 1-Nov", title: "LangGraph: Stateful Workflows and Routing", focus: "State, nodes, edges, streaming, LangGraph Studio" },
        { date: "Sun 7-Nov", title: "LangGraph: Cycles, HITL and Persistence", focus: "Loops, human approval, checkpointers, guardrails" },
        { date: "Sat 8-Nov", title: "Multi-Agent Orchestration with CrewAI", focus: "Crews, flows, managers, memory, observability" },
        { date: "Sun 14-Nov", title: "Multi-Agent Systems with Microsoft AutoGen", focus: "AgentChat, teams, GraphFlow, memory" },
        { date: "Sat 15-Nov", title: "Agentic RAG and GraphRAG for Agents", focus: "Self-RAG, CRAG, reranking, GraphRAG, RAGAS" },
        { date: "Sun 21-Nov", title: "Deep Agents: Reflection, Planning and Memory", focus: "Reflection, replanning, long-term memory" },
      ],
    },
  ],
};
