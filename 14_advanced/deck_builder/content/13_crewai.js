const M = "13_crew_ai/";

module.exports = {
  section: "Module 13 – CrewAI",
  slides: [
    {
      kind: "opener",
      eyebrow: "Module 13",
      title: "Multi-Agent Orchestration with CrewAI",
      subtitle: "Teams of role-playing agents (crews) and the event-driven flows that control them",
      goals: [
        { icon: "FaPeopleGroup", title: "Build crews from agents and tasks", text: "roles, goals, backstories, tools and processes" },
        { icon: "FaDiagramProject", title: "Control execution with Flows", text: "@start, @listen, @router and shared state" },
        { icon: "FaUserTie", title: "Delegate with managers and humans", text: "hierarchical crews, levels of autonomy" },
        { icon: "FaShieldHalved", title: "Make crews reliable", text: "memory, structured output, guardrails" },
      ],
      agenda: [
        "CrewAI concepts: agents, tasks, crews",
        "From a basic crew to an advanced one",
        "Crew vs Flow; Flow building blocks",
        "Building a flow with conditional routing",
        "Hierarchical crews and manager agents",
        "Human-in-the-loop and controlled autonomy",
        "Memory, knowledge and structured output",
        "Guardrails, error handling and reliability",
      ],
    },
    {
      title: "What Is CrewAI?",
      subtitle: "A Python framework where AI agents with different roles collaborate on complex tasks",
      demo: M + "13_1_crewai_basics.py",
      blocks: [
        { type: "cards", size: 10.5, items: [
          { icon: "FaUser", title: "Agents", tag: "Team members", lines: ["**Role:** what they do", "**Goal:** what they aim for", "**Backstory:** context that sharpens them", "**Tools:** what they can call"] },
          { icon: "FaListCheck", title: "Tasks", tag: "Assignments", lines: ["**Description:** what to do", "**Expected output:** format and content", "**Agent:** who does it"] },
          { icon: "FaUserTie", title: "Crew", tag: "Team lead", lines: ["Delegates tasks", "Coordinates the agents", "Runs the process", "Combines the results"] },
          { icon: "FaScrewdriverWrench", title: "Tools", tag: "Utilities", lines: ["File readers, web search, APIs, databases", "Custom tools for your domain"] },
        ] },
      ],
    },
    {
      title: "From a Basic Crew to an Advanced One",
      subtitle: "A simple crew runs tasks in order; advanced applications also need orchestration, state and control",
      demo: M + "13_1_crewai_basics.py",
      blocks: [
        { type: "flow", items: [
          { icon: "FaMagnifyingGlass", label: "Agent 1", caption: "Research" },
          { icon: "FaChartLine", label: "Agent 2", caption: "Analysis" },
          { icon: "FaPen", label: "Agent 3", caption: "Writing" },
          { icon: "FaUserTie", label: "Crew", caption: "Orchestrates all three", color: "coral" },
        ] },
        { type: "cols", ratio: [1.45, 1], cols: [
          [{ type: "chain", items: ["Agent", "Task", "Crew"] }, { type: "chain", gapBefore: 0.12, items: ["Agent", "Orchestration", "State", "Control"], highlight: [1, 2, 3] }],
          [{ type: "callout", eyebrow: "Advanced crews must answer", text: "What should happen next? · Which agent should act? · What carries forward? · What if the result is poor? · Where should a human step in?" }],
        ] },
      ],
    },
    { kind: "image", src: "crewai_context_memory.png", alt: "How context and memory work in CrewAI", demo: "Concept" },

    // ---------------------------------------------------------------- flows
    {
      title: "Crew vs Flow",
      subtitle: "Crew = who does the work.  Flow = how the application runs.",
      demo: M + "13_2_crew_vs_flow.py",
      blocks: [
        { type: "compare", size: 11.5, cols: [
          { title: "Crew", color: "navy", items: ["A team of agents working together", "Focus: collaboration", "Agents perform the tasks", "Good for multi-agent work"] },
          { title: "Flow", color: "teal", items: ["Controls the overall application", "Focus: orchestration", "Decides what happens next", "Good for complex, branching workflows"] },
        ] },
        { type: "chain", items: ["START", "Research", "Evaluate", "Good → Analyze → Report", "Poor → Research again"], highlight: [2] },
      ],
    },
    {
      title: "Flow Building Blocks",
      subtitle: "Four decorators plus a shared state",
      demo: M + "13_2_crew_vs_flow.py",
      blocks: [
        { type: "tiles", cols: 4, items: [
          { icon: "FaPlay", title: "@start", text: "Where the flow begins (there can be several)" },
          { icon: "FaEarListen", title: "@listen", text: "Run when another step's output arrives" },
          { icon: "FaCodeBranch", title: "@router", text: "Choose which path to take" },
          { icon: "FaDatabase", title: "State", text: "Read → update → pass forward" },
        ] },
        { type: "cols", ratio: [1, 1.1], cols: [
          [{ type: "code", caption: "Routing on confidence", code:
`@router(fetch_snapshot)
def route_on_confidence(self):
    if self.state.confidence >= 0.8:
        return "good"
    return "retry"` }],
          [{ type: "bullets", size: 11, items: [
            "Listeners subscribe to the route labels: `@listen(\"good\")` and `@listen(\"retry\")`",
            "Branches can converge again with `or_(…)`",
            "No hard-coded sequence – the flow decides at run time",
          ] }],
        ] },
      ],
    },
    {
      title: "Building a Flow: Stock Research",
      subtitle: "Fetch a live snapshot, judge its quality, then analyse it with a crew – or explain why not",
      demo: M + "13_2_crew_vs_flow.py",
      split: [1.25, 1],
      left: [
        { type: "code", caption: "13_2_crew_vs_flow.py (condensed)", code:
`class ResearchState(BaseModel):
    ticker: str = "AAPL"
    snapshot: str = ""
    confidence: float = 0.0
    report: str = ""

class StockResearchFlow(Flow[ResearchState]):
    @start()
    def fetch_snapshot(self): ...      # yfinance
    @router(fetch_snapshot)
    def route_on_confidence(self): ... # good | retry
    @listen("retry")
    def handle_low_confidence(self): ...
    @listen("good")
    def analyze_with_crew(self): ...   # Crew.kickoff()
    @listen(or_(handle_low_confidence,
                analyze_with_crew))
    def finalize_report(self): ...` },
      ],
      right: [
        { type: "steps", size: 10.5, gap: 0.1, items: [
          { title: "State", text: "A Pydantic model shared by every step" },
          { title: "@start", text: "Fetch the stock snapshot; confidence = share of fields present" },
          { title: "@router", text: "≥ 0.8 → \"good\", otherwise \"retry\"" },
          { title: "@listen(\"good\")", text: "An equity-analyst crew writes the take" },
          { title: "or_(…)", text: "Both branches converge in finalize_report" },
        ] },
      ],
    },

    // ---------------------------------------------------------------- control
    {
      title: "Hierarchical Crews and Manager Agents",
      subtitle: "Instead of a fixed researcher → analyst → writer chain, a manager decides who does what",
      demo: M + "13_3_hierarchical_crew.py",
      blocks: [
        { type: "cols", ratio: [1.1, 1], cols: [
          [{ type: "tree", boxW: 1.6, rows: [[{ label: "Manager agent", fill: "coral" }], ["Research", "Data", "Critic"], [{ label: "Final output", fill: "navy" }]] }],
          [{ type: "bullets", size: 11.5, items: ["Understands the overall objective", "Delegates work to specialists", "Reviews their results", "Decides what needs more work", "Coordinates the final output"] }],
        ] },
        { type: "callout", eyebrow: "Use it only when needed", text: "If the workflow is straightforward and not agentic, a sequential crew is simpler and cheaper than a manager agent." },
      ],
    },
    {
      title: "Human-in-the-Loop and Controlled Autonomy",
      subtitle: "Decide how much the crew may do on its own",
      demo: M + "13_4_human_in_the_loop.py",
      split: [1.35, 1],
      left: [
        { type: "table", size: 10.5, widths: [1.7, 1.6, 1.8], head: ["Level", "Agent behaviour", "Example"], rows: [
          ["Human-in-the-loop", "A human approves each action", "Approve a refund"],
          ["Human-on-the-loop", "A human supervises", "Monitor automated decisions"],
          ["Human-out-of-the-loop", "Fully autonomous", "Automated classification"],
        ] },
      ],
      right: [
        { type: "tree", boxW: 1.6, rows: [["Agent"], ["Recommendation"], [{ label: "Human review", fill: "coral" }], [{ label: "Approve → Execute", fill: "teal" }, "Reject → Revise"]] },
      ],
    },
    {
      title: "Memory, Knowledge and Structured Output",
      subtitle: "What agents know, what they remember – and how they hand results to each other reliably",
      demo: M + "13_5_memory_and_knowledge.py, " + M + "13_6_structured_outputs.py",
      blocks: [
        { type: "cols", ratio: [1, 1.2], cols: [
          [
            { type: "icons", d: 0.38, size: 11, items: [
              { icon: "FaBook", title: "Knowledge", text: "\"What information do I need to know?\" – documents given up front" },
              { icon: "FaMemory", title: "Memory", text: "\"What do I remember from earlier work?\" – retrieved when needed" },
              { icon: "FaDatabase", title: "Flow state ≠ memory", text: "State is this run's temporary context; memory outlives it" },
            ] },
          ],
          [
            { type: "chain", items: ["Agent", "Structured output", "Validated schema", "Next agent"], highlight: [2] },
            { type: "code", caption: "13_6_structured_outputs.py", code:
`class ResearchFinding(BaseModel):
    company: str
    revenue_growth: float   # 0.12 = 12%
    risk_level: str         # low | medium | high
    confidence: float       # 0-1
    evidence: list[str]` },
          ],
        ] },
      ],
    },
    {
      title: "Guardrails, Error Handling and Reliability",
      subtitle: "Agents fail – plan for it",
      demo: M + "13_7_guardrails_and_reliability.py",
      blocks: [
        { type: "cols", cols: [
          [
            { type: "text", text: "**Why agents fail**", size: 12.5 },
            { type: "bullets", size: 11, items: ["Hallucinate", "Return incomplete information", "Call the wrong tool", "Produce invalid output", "Get stuck in a loop", "Depend on a service that is down"] },
          ],
          [
            { type: "text", text: "**What a guardrail checks**", size: 12.5 },
            { type: "bullets", size: 11, items: ["Required fields exist", "The answer contains evidence", "Confidence is above a threshold", "Output follows policy", "SQL is read-only", "Values are within an allowed range"] },
          ],
        ] },
        { type: "chain", items: ["Format", "Content", "Quality", "Safety / policy"], highlight: [0, 1, 2, 3] },
      ],
    },
    {
      kind: "summary",
      title: "Module 13 Summary",
      subtitle: "What you built",
      built: [
        { tag: "13_1", title: "A first crew", text: "Agents, tasks and a crew that combines their work" },
        { tag: "13_2", title: "A Flow", text: "@start, @router and @listen around a stock-analysis crew" },
        { tag: "13_3", title: "Hierarchical crew", text: "A manager agent delegating to specialists" },
        { tag: "13_6", title: "Reliable hand-offs", text: "Pydantic outputs and guardrails between agents" },
      ],
      takeaways: [
        "A crew is about who works; a flow is about what happens next",
        "Clear roles, goals and expected outputs make agents dependable",
        "Use a manager agent only when the work needs judgement",
        "Pass structured data between agents, not free text",
        "Validate format, content, quality and policy",
      ],
      next: "Module 14: Agentic RAG and GraphRAG",
    },
  ],
};
