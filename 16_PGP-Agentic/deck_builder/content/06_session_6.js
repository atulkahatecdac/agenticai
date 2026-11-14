const S = "session_6/";

module.exports = {
  section: "Session 6 – CrewAI",
  slides: [
    {
      kind: "opener",
      eyebrow: "Session 6",
      title: "Multi-Agent Orchestration with CrewAI",
      subtitle: "Teams of role-playing agents (crews) and the event-driven flows that control them",
      goals: [
        { icon: "FaPeopleGroup", title: "Build crews from agents and tasks", text: "roles, goals, tools, context and memory" },
        { icon: "FaDiagramProject", title: "Control execution with Flows", text: "@start, @listen, @router and shared state" },
        { icon: "FaUserTie", title: "Delegate with managers and humans", text: "hierarchical crews, levels of autonomy" },
        { icon: "FaShieldHalved", title: "Make crews reliable and observable", text: "guardrails, error handling, LangSmith" },
      ],
      agenda: [
        "CrewAI concepts: agents, tasks, crews",
        "Context and memory",
        "Crew vs Flow, and conditional routing",
        "Hierarchical crews and manager agents",
        "Human-in-the-loop and controlled autonomy",
        "Guardrails, error handling and reliability",
        "Observability with LangSmith",
      ],
    },
    {
      title: "What Is CrewAI?",
      subtitle: "A Python framework where AI agents with different roles collaborate on complex tasks",
      demo: S + "6_1_crewai_basics.py",
      blocks: [
        { type: "cards", size: 10.5, items: [
          { icon: "FaUser", title: "Agents", tag: "Team members", lines: ["**Role:** what they do", "**Goal:** what they aim for", "**Backstory:** context that sharpens them", "**Tools:** what they can call"] },
          { icon: "FaListCheck", title: "Tasks", tag: "Assignments", lines: ["**Description:** what to do", "**Expected output:** format and content", "**Agent:** who does it", "e.g. \"Explain {topic} to a beginner\""] },
          { icon: "FaUserTie", title: "Crew", tag: "Team lead", lines: ["Delegates tasks", "Coordinates the agents", "Runs the process", "Combines the results"] },
          { icon: "FaScrewdriverWrench", title: "Tools", tag: "Utilities", lines: ["File readers, web search, APIs, databases", "Custom tools for your domain"] },
        ] },
      ],
    },
    {
      title: "Context and Memory",
      subtitle: "Context passes work forward inside one run; memory carries facts from one run to the next",
      demo: S + "6_2_crewai_context_and_memory.py",
      split: [1, 1],
      left: [
        { type: "flow", items: [
          { icon: "FaMagnifyingGlass", label: "Analyst", caption: "fetch_task: StockSnapshot tool" },
          { icon: "FaPen", label: "Writer", caption: "brief_task gets the snapshot" },
        ] },
        { type: "code", caption: "Context – inside one run", code:
`brief_task = Task(
    description="Using the snapshot, write ...",
    agent=writer,
    context=[fetch_task],
)` },
      ],
      right: [
        { type: "flow", items: [
          { icon: "FaApple", label: "Run 1: AAPL", caption: "saves margin 27.6%, growth 11.7%" },
          { icon: "FaDatabase", label: "Memory", caption: "short-term, long-term, entity", color: "coral" },
          { icon: "FaWindows", label: "Run 2: MSFT", caption: "recalls Apple's figures" },
        ] },
        { type: "code", caption: "Memory – across runs", code:
`crew = Crew(..., memory=True,
            entity_memory=RecallEntityMemory())
crew.kickoff(inputs={"ticker": "AAPL", ...})
crew.kickoff(inputs={"ticker": "MSFT", ...})` },
        { type: "callout", size: 11, eyebrow: "Why RecallEntityMemory", text: "CrewAI drops matches below 0.6; Apple's facts scored ~0.5, so 6_2 uses 0.45." },
      ],
    },
    // ---------------------------------------------------------------- flows
    {
      title: "Crew vs Flow",
      subtitle: "Crew = who does the work.  Flow = Manager who decides how the application runs.",
      demo: S + "6_3_crew_vs_flow.py",
      blocks: [
        { type: "compare", size: 11.5, cols: [
          { title: "Crew", color: "navy", items: ["A team of agents working together", "Focus: collaboration", "Agents perform the tasks", "Good for multi-agent work"] },
          { title: "Flow", color: "teal", items: ["Controls the overall application", "Focus: orchestration", "Decides what happens next", "Good for complex, branching workflows"] },
        ] },
        { type: "chain", items: ["START", "Fetch snapshot", "Route on confidence", "Good → Crew analysis → Report", "Retry → Explain why not → Report"], highlight: [2] },
      ],
    },
    {
      title: "Flow Building Blocks",
      subtitle: "Three decorators",
      blocks: [
        { type: "tiles", cols: 3, items: [
          { icon: "FaPlay", title: "@start", text: "Where the flow begins (there can be several)" },
          { icon: "FaEarListen", title: "@listen", text: "Run when another step's output arrives" },
          { icon: "FaCodeBranch", title: "@router", text: "Choose which path to take" },
        ] },
        { type: "cols", ratio: [1, 1], cols: [
          [{ type: "code", size: 7.8, code:
`class BlogFlow(Flow):
    @start()
    def pick_topic(self):
        self.state["topic"] = "AI agents"

    @listen(pick_topic)
    def write_draft(self):
        # hand off to a Crew of writer agents
        return WriterCrew().crew().kickoff(
            inputs={"topic": self.state["topic"]})

    @router(write_draft)
    def check_quality(self, draft):
        return "publish" if len(str(draft)) > 500 else "rewrite"` }],
          [{ type: "code", size: 7.8, code:
`    @listen("publish")
    def publish(self):
        print("Published!")

    @listen("rewrite")
    def rewrite(self):
        return WriterCrew().crew().kickoff(
            inputs={"topic": self.state["topic"],
                    "note": "Make it longer and deeper"})` }],
        ] },
        { type: "callout", text: "**Problem:** rewrite would run once and stop. How to make rewrite go back through the quality check?" },
      ],
    },
    {
      title: "Flow Looping",
      subtitle: "Using **or_**",
      blocks: [
        { type: "callout", text: "By default, the rewrite function would execute only once – to make it run till we get a satisfactory result, we need to make it loop. Now the quality check router listens to both write and rewrite." },
        { type: "code", code:
`from crewai.flow.flow import or_

@router(or_(write_draft, rewrite))
def check_quality(self, draft):
    return "publish" if len(str(draft)) > 500 else "rewrite"` },
        { type: "callout", text: "**Note:** This may result into an endless loop. Add a retry counter in self.state so that it cannot loop forever if the rewrite is never satisfactory." },
      ],
    },
    {
      title: "Building a Flow: Stock Research",
      subtitle: "Fetch a live snapshot, judge its quality, then analyse it with a crew – or explain why not",
      demo: S + "6_3_crew_vs_flow.py",
      split: [1.25, 1],
      left: [
        { type: "code", caption: "6_3_crew_vs_flow.py (condensed)", code:
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
      title: "Crew Process: Sequential or Hierarchical",
      subtitle: "How the agents inside one crew share the work – Process is inside a crew, Flow is around crews",
      blocks: [
        { type: "compare", size: 10.5, codeSize: 8.5, cols: [
          { title: "Sequential – an assembly line", color: "navy", items: [
            "Tasks run in order, each output feeding the next; you assign every agent. The default.",
          ], code:
`crew = Crew(
    agents=[researcher, writer],
    tasks=[research_task, write_task],
    process=Process.sequential,
)` },
          { title: "Hierarchical – a team with a boss", color: "teal", items: [
            "A manager agent delegates, reviews and can send work back. Needs `manager_llm` or `manager_agent`.",
          ], code:
`crew = Crew(
    agents=[researcher, writer, editor],
    tasks=[research_task, write_task],
    process=Process.hierarchical,
    manager_llm="gpt-4o",  # or manager_agent=...
)` },
        ] },
        { type: "cols", ratio: [1.25, 1], cols: [
          [{ type: "callout", eyebrow: "Which to pick?", text: "**Sequential:** known steps – cheaper, faster, easier to debug. **Hierarchical:** open-ended work – more calls, less predictable." }],
          [{ type: "callout", eyebrow: "\"Hybrid\"", text: "Not a setting – a Flow runs a sequential crew in one step, a hierarchical one in another." }],
        ] },
      ],
    },
    {
      title: "Hierarchical Crews and Manager Agents",
      subtitle: "Instead of a fixed researcher → analyst → writer chain, a manager decides who does what",
      demo: S + "6_4_hierarchical_crew.py",
      blocks: [
        { type: "cols", ratio: [1.1, 1], cols: [
          [{ type: "tree", boxW: 1.6, rows: [[{ label: "Research Manager", fill: "coral" }], ["Fundamentals", "News & Sentiment", "Valuation"], [{ label: "Final output", fill: "navy" }]] }],
          [{ type: "bullets", size: 11.5, items: ["Understands the overall objective", "Delegates work to specialists", "Reviews their results", "Decides what needs more work", "Coordinates the final output"] }],
        ] },
        { type: "callout", eyebrow: "Use it only when needed", text: "If the workflow is straightforward and not agentic, a sequential crew is simpler and cheaper than a manager agent." },
      ],
    },
    {
      title: "Human-in-the-Loop and Controlled Autonomy",
      subtitle: "Decide how much the crew may do on its own",
      demo: S + "6_5_human_in_the_loop.py",
      split: [1.35, 1],
      left: [
        { type: "table", size: 10.5, widths: [1.7, 1.6, 1.8], head: ["Level", "Agent behaviour", "Example"], rows: [
          ["Human-in-the-loop", "A human approves each action", "Approve a trade recommendation (this demo)"],
          ["Human-on-the-loop", "A human supervises", "A review dashboard"],
          ["Human-out-of-the-loop", "Fully autonomous", "The snapshot summary in 6_2"],
        ] },
      ],
      right: [
        { type: "tree", boxW: 1.6, rows: [["Agent"], ["Recommendation"], [{ label: "Human review", fill: "coral" }], [{ label: "Approve → Execute", fill: "teal" }, "Reject → Revise"]] },
      ],
    },
    {
      title: "Guardrails, Error Handling and Reliability",
      subtitle: "Agents fail – plan for it",
      demo: S + "6_6_guardrails_and_reliability.py",
      blocks: [
        { type: "cols", cols: [
          [
            { type: "text", text: "**Why agents fail**", size: 12.5 },
            { type: "bullets", size: 11, items: ["Hallucinate", "Return incomplete information", "Call the wrong tool", "Produce invalid output", "Get stuck in a loop", "Depend on a service that is down"] },
          ],
          [
            { type: "text", text: "**What a guardrail checks**", size: 12.5 },
            { type: "bullets", size: 11, items: ["**In the demo:** states buy, hold or sell", "**In the demo:** gives reasoning, not one word", "**In the demo:** any claimed price is near the real one", "Also common: required fields, evidence, confidence", "Also common: read-only SQL, allowed value ranges"] },
          ],
        ] },
        { type: "chain", items: ["Format", "Content", "Quality", "Safety / policy"], highlight: [0, 1, 2, 3] },
      ],
    },
    {
      title: "Observability with LangSmith",
      subtitle: "See every agent step, prompt, tool call and token count",
      demo: S + "6_7_crewai_observability.py",
      split: [1, 1.1],
      left: [
        { type: "steps", items: [
          { title: "Sign up at smith.langchain.com" },
          { title: "Create a tracing project", text: "Tracing → New → market-research-crew" },
          { title: "Add the settings to .env" },
          { title: "Run the crew and open the trace" },
        ] },
      ],
      right: [
        { type: "code", caption: ".env", code:
`LANGSMITH_TRACING="true"
LANGSMITH_ENDPOINT="https://api.smith.langchain.com"
LANGSMITH_API_KEY="your api key"
LANGSMITH_PROJECT="market-research-crew"` },
      ],
    },
    {
      kind: "summary",
      title: "Session 6 Summary",
      subtitle: "What you built today",
      built: [
        { tag: "6_1", title: "A first crew", text: "One agent, one task, on a local model" },
        { tag: "6_2", title: "Context and memory", text: "Hand-offs inside a run, recall across runs" },
        { tag: "6_3", title: "A Flow", text: "@start, @router and @listen around a stock-analysis crew" },
        { tag: "6_4", title: "Hierarchical crew", text: "A manager agent delegating to specialists" },
        { tag: "6_6", title: "Guardrails", text: "Checks that reject a bad answer before it moves on" },
      ],
      takeaways: [
        "A crew is about who works; a flow is about what happens next",
        "Clear roles, goals and expected outputs make agents dependable",
        "Use a manager agent only when the work really needs judgement",
        "Context passes work inside a run; memory carries it across runs",
        "Trace everything – multi-agent bugs are hard to see otherwise",
      ],
      next: "Session 7: Microsoft Agent Framework and AutoGen",
    },
  ],
};
