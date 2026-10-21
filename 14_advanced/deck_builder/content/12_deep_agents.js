const M = "12_deep_agents/";

module.exports = {
  section: "Module 12 – Deep Agents",
  slides: [
    {
      kind: "opener",
      eyebrow: "Module 12",
      title: "Deep Agents: Reflection, Planning and Memory",
      subtitle: "Agents that check their own work, plan and re-plan, remember, and get better from their mistakes",
      goals: [
        { icon: "FaMagnifyingGlassChart", title: "Add self-reflection", text: "generate, critique and revise until a quality bar is met" },
        { icon: "FaListOl", title: "Plan, execute and re-plan", text: "and choose between ReAct and plan-and-execute" },
        { icon: "FaMemory", title: "Give agents long-term memory", text: "episodic, semantic, procedural – and consolidation" },
        { icon: "FaBrain", title: "Know when to doubt", text: "confidence estimation and learning from failures" },
      ],
      agenda: [
        "What makes an agent \"deep\"",
        "Self-reflection and multi-turn reflection",
        "Plan-and-execute and replanning",
        "ReAct vs plan-and-execute",
        "Long-term memory types; episodic memory",
        "Memory consolidation",
        "Confidence and uncertainty",
        "Self-improvement from failures",
        "One unified architecture",
      ],
    },
    {
      title: "What Makes an Agent \"Deep\"",
      subtitle: "It doesn't just produce an answer – it evaluates its own process and adapts",
      demo: "Concept",
      blocks: [
        { type: "text", text: "**Basic agent**", size: 12 },
        { type: "chain", gapBefore: 0.08, items: ["User", "LLM", "Tool", "Answer"] },
        { type: "text", text: "**Deeper agent**", size: 12 },
        { type: "chain", gapBefore: 0.08, items: ["User", "Think about the task", "Plan", "Act", "Observe", "Evaluate", "Revise strategy", "Answer"], highlight: [5, 6] },
        { type: "compare", size: 11.5, cols: [
          { title: "Normal reasoning", color: "slate", items: ["\"How do I solve this?\""] },
          { title: "Meta-cognition", color: "teal", items: ["\"Is my way of solving this working?\""] },
        ] },
      ],
    },
    {
      title: "Self-Reflection: Generate → Critique → Revise",
      subtitle: "\"Explain RAG to a beginner in 200 words\"",
      demo: "Concept",
      blocks: [
        { type: "flow", loop: "repeat while the critique finds issues", items: [
          { icon: "FaPen", label: "Generate", caption: "Input → LLM → draft" },
          { icon: "FaClipboardCheck", label: "Critique", caption: "Score the draft against a rubric", color: "coral" },
          { icon: "FaWandMagicSparkles", label: "Revise", caption: "Draft + critique → improved answer", color: "teal" },
        ] },
        { type: "cols", cols: [
          [{ type: "table", size: 10, widths: [1.5, 2], head: ["Rubric", "Verdict"], rows: [
            ["Accuracy", "Good"], ["Completeness", "Missing indexing / vector search"], ["Clarity, level, length", "Good, within limit"],
          ] }],
          [{ type: "callout", eyebrow: "Issues to fix", text: "1. Explain retrieval more clearly  2. Say why embeddings are used  3. Show how the retrieved context reaches the LLM" }],
        ] },
      ],
    },
    {
      title: "Multi-Turn Reflection",
      subtitle: "Iterate until a quality threshold is met – with an upper limit on rounds",
      demo: M + "meal_plan_reflection.py",
      blocks: [
        { type: "chain", items: ["Generate", "Critique: 6 / 10", "Revise", "Critique: 7.5 / 10", "Revise", "Critique: 9 / 10", "STOP"], highlight: [6] },
        { type: "tiles", cols: 5, size: 10, titleSize: 11, items: [
          { icon: "FaBullseye", title: "Accuracy" },
          { icon: "FaListCheck", title: "Completeness" },
          { icon: "FaCrosshairs", title: "Relevance" },
          { icon: "FaEye", title: "Clarity" },
          { icon: "FaBook", title: "Evidence" },
        ] },
        { type: "text", size: 11.5, color: "slate", text: "The critic can score several dimensions and average them. Cap the number of loops so a picky critic can't run forever." },
      ],
    },
    {
      title: "Plan-and-Execute",
      subtitle: "Planning decides what to do (strategy); execution does it (action)",
      demo: M + "study_plan_plan_execute.py",
      split: [1.2, 1],
      left: [
        { type: "text", text: "**\"Research three competitors, compare their pricing, identify their strengths, and recommend one.\"**", size: 11.5 },
        { type: "steps", size: 10.5, titleSize: 11, gap: 0.06, items: [
          "Identify three competitors", "Research competitor A", "Research competitor B", "Research competitor C",
          "Collect pricing", "Compare features and pricing", "Identify strengths and weaknesses", "Make a recommendation",
        ] },
      ],
      right: [
        { type: "icons", d: 0.42, items: [
          { icon: "FaListOl", title: "Planner", text: "Writes the numbered plan once, up front" },
          { icon: "FaPersonRunning", title: "Executor", text: "Carries out each step with the right tools" },
          { icon: "FaGraduationCap", title: "In the demo", text: "A study plan built and then executed step by step" },
        ] },
      ],
    },
    {
      title: "Replanning",
      subtitle: "Update the plan when new information arrives – during execution the agent may discover that…",
      demo: M + "pathology_report_replanning.py",
      blocks: [
        { type: "tiles", cols: 4, size: 10.5, items: [
          { icon: "FaBan", title: "A resource is unavailable" },
          { icon: "FaPlugCircleXmark", title: "A tool fails" },
          { icon: "FaTriangleExclamation", title: "Facts contradict an assumption" },
          { icon: "FaBolt", title: "New information changes things" },
          { icon: "FaCircleCheck", title: "A task is already done" },
          { icon: "FaLinkSlash", title: "A dependency is missing" },
          { icon: "FaHourglassHalf", title: "The approach is too slow or costly" },
          { icon: "FaFileMedical", title: "In the demo", text: "A pathology report changes the plan" },
        ] },
      ],
    },
    {
      title: "ReAct vs Plan-and-Execute",
      subtitle: "ReAct picks the next action from the latest observation; plan-and-execute plans at a higher level first",
      demo: "Concept",
      blocks: [
        { type: "table", size: 10.5, widths: [1.8, 2.2, 2.2], head: ["Dimension", "ReAct", "Plan-and-Execute"], rows: [
          ["Planning", "Incremental", "Up front"],
          ["Decisions", "At every step", "At plan level"],
          ["Adaptability", "Very high", "High, with replanning"],
          ["Simple tasks", "**Excellent**", "Often overkill"],
          ["Long workflows", "Can get messy", "**Better suited**"],
          ["Debugging", "Harder", "Easier"],
          ["Parallel steps", "Less natural", "Easier"],
          ["Planning overhead", "Low", "Higher"],
          ["Transparency", "Action by action", "An explicit plan"],
        ] },
      ],
    },

    // ---------------------------------------------------------------- memory
    {
      title: "Long-Term Memory: Three Kinds",
      subtitle: "Episodic = experiences.  Semantic = knowledge.  Procedural = skills.",
      demo: "Concept",
      blocks: [
        { type: "cards", size: 11, items: [
          { icon: "FaClockRotateLeft", title: "Episodic", tag: "What happened?", lines: ["\"We discussed Project X last Tuesday.\""] },
          { icon: "FaBook", title: "Semantic", tag: "What do I know?", lines: ["\"Project X uses PostgreSQL.\""] },
          { icon: "FaGears", title: "Procedural", tag: "How do I do it?", lines: ["\"Deploy Project X using this procedure.\""] },
        ] },
        { type: "text", size: 11, color: "slate", text: "All three live outside the model – in a database or vector store – and are pulled into the prompt when relevant." },
      ],
    },
    {
      title: "Episodic Memory in Practice",
      subtitle: "Store specific past episodes outside the model and recall them when a similar case arrives",
      demo: M + "episodic_memory_store.py",
      blocks: [
        { type: "flow", items: [
          { icon: "FaDatabase", label: "Seed", caption: "324 past support tickets, one text blob each" },
          { icon: "FaMagnifyingGlass", label: "recall()", caption: "Find the 2 most similar episodes" },
          { icon: "FaFileLines", label: "Prompt", caption: "\"Here is how similar questions were answered\"" },
          { icon: "FaReply", label: "Answer", caption: "Grounded in past resolutions" },
          { icon: "FaFloppyDisk", label: "remember()", caption: "Store this Q and A as a new episode", color: "coral" },
        ] },
        { type: "code", caption: "Each episode", code: `"Customer asked: Why was my payment declined? | Resolution: ..."` },
        { type: "text", size: 11, color: "slate", text: "Unlike a fixed knowledge base, the store keeps growing as the agent handles new cases." },
      ],
    },
    {
      title: "Memory Consolidation",
      subtitle: "Summarise and compress old episodes before they pile up",
      demo: M + "memory_consolidation.py",
      blocks: [
        { type: "compare", size: 11, cols: [
          { title: "Without consolidation", color: "slate", items: ["Day 1 → episode 1 … day 100 → episode 100", "Large, redundant, expensive to search", "Hard to reason over"] },
          { title: "With consolidation", color: "teal", items: ["Find common patterns across episodes", "Replace each group with one dense summary", "Swap the summaries into the vector store"] },
        ] },
        { type: "chain", items: ["8 episodes", "3 patterns: 2FA issue · card declined · subscription cancellation", "3 summaries"], highlight: [2] },
      ],
    },
    {
      title: "Confidence and Uncertainty",
      subtitle: "An LLM sounds just as sure when it is guessing – so make the agent estimate and act on its confidence",
      demo: "Concept",
      split: [1, 1.1],
      left: [
        { type: "tree", boxW: 1.7, size: 10.5, boxH: 0.36, rows: [["User question"], ["Agent"], [{ label: "Answer + confidence", fill: "navy" }], [{ label: "High → answer", fill: "teal" }, { label: "Low → flag / verify / ask / escalate", fill: "coral" }]] },
      ],
      right: [
        { type: "text", text: "**Low confidence is likely when there is…**", size: 11.5 },
        { type: "bullets", size: 11, items: [
          "Insufficient information",
          "Conflicting evidence",
          "Weak retrieval results",
          "Ambiguous user intent",
          "No reliable source",
          "Uncertain reasoning",
        ] },
      ],
    },
    {
      title: "Self-Improvement from Failures",
      subtitle: "Learn corrected facts from mistakes – good answers leave no trace, mistakes leave a lesson",
      demo: M + "self_improving_agent.py",
      blocks: [
        { type: "flow", items: [
          { icon: "FaMagnifyingGlass", label: "recall_lessons", caption: "Any past lessons relevant to this query?" },
          { icon: "FaReply", label: "respond", caption: "Answer, guided by recalled lessons" },
          { icon: "FaGavel", label: "evaluate", caption: "An LLM judge grades against the real policy; 7+ only for the specific correct fact", color: "coral" },
          { icon: "FaFloppyDisk", label: "maybe_store_lesson", caption: "Only if score < 7: store the corrected fact, not the bad answer", color: "teal" },
        ] },
        { type: "text", size: 11.5, color: "slate", text: "This is semantic memory (facts), not episodic: who asked and when are stripped away." },
      ],
    },
    {
      title: "One Unified Deep-Agent Architecture",
      subtitle: "Memory informs planning → planning guides execution → reflection evaluates it → replanning adapts",
      demo: "Concept",
      blocks: [
        { type: "flow", loop: "not good enough → replan", items: [
          { icon: "FaMemory", label: "Memory", caption: "What do I know?" },
          { icon: "FaListOl", label: "Planning", caption: "What should I do?" },
          { icon: "FaPersonRunning", label: "Execution", caption: "How do I act?" },
          { icon: "FaMagnifyingGlassChart", label: "Reflection", caption: "Is it working?", color: "coral" },
          { icon: "FaRoute", label: "Replanning", caption: "What should change?", color: "teal" },
        ] },
        { type: "callout", eyebrow: "Putting it together", text: "Retrieve past experience, decompose the task, act with tools, evaluate progress – then finish, or go back and plan again." },
      ],
    },
    {
      kind: "summary",
      title: "Module 12 Summary",
      subtitle: "What you built",
      built: [
        { tag: "reflect", title: "Reflection loops", text: "A meal plan critiqued and revised to a quality bar" },
        { tag: "plan", title: "Plan and replan", text: "A study plan; a plan that changes with a pathology report" },
        { tag: "memory", title: "Episodic memory", text: "Support tickets recalled, then consolidated" },
        { tag: "learn", title: "Self-improving agent", text: "Lessons stored only when the agent was wrong" },
      ],
      takeaways: [
        "Deep agents evaluate how they are doing, not just what to do",
        "Reflection needs a rubric and a stopping rule",
        "Plan up front for long tasks; replan when facts change",
        "Choose the memory type by what must be remembered",
        "Act on confidence – escalate when unsure",
      ],
      next: "Module 13: CrewAI",
    },
  ],
};
