const S = "session_9/";

module.exports = {
  section: "Session 9 – Deep Agents",
  slides: [
    {
      kind: "opener",
      eyebrow: "Session 9",
      title: "Deep Agents: Reflection, Planning and Memory",
      subtitle: "Agents that check their own work, plan and re-plan, remember, and get better from their mistakes",
      goals: [
        { icon: "FaMagnifyingGlassChart", title: "Add self-reflection", text: "generate, critique and revise until a quality bar is met" },
        { icon: "FaListOl", title: "Plan, execute and re-plan", text: "plans that change when new facts arrive" },
        { icon: "FaMemory", title: "Give agents long-term memory", text: "episodic, semantic and procedural – plus consolidation" },
        { icon: "FaBrain", title: "Combine it all", text: "context management, self-improvement, one unified architecture" },
      ],
      agenda: [
        "What makes an agent \"deep\"",
        "Self-reflection loops",
        "Multi-turn reflection with a quality threshold",
        "Plan-and-Execute",
        "Replanning",
        "Long-term memory types",
        "Episodic memory",
        "Memory consolidation",
        "Context propagation and trimming",
        "Self-improvement from failures",
        "Unified architecture: reflection + planning + memory",
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
      subtitle: "\"Write a customer-facing outage update\"",
      demo: S + "9_1_openai_agent_pattern_reflection.py",
      blocks: [
        { type: "flow", items: [
          { icon: "FaPen", label: "draft", caption: "A first customer message" },
          { icon: "FaClipboardCheck", label: "reflection", caption: "Critique it against a checklist", color: "coral" },
          { icon: "FaWandMagicSparkles", label: "revised_answer", caption: "Rewrite using the critique", color: "teal" },
        ] },
        { type: "cols", cols: [
          [{ type: "bullets", size: 11, items: ["Clear for non-technical users", "Accountable without blaming individuals", "Honest about impact", "Specific about next steps and prevention"] }],
          [{ type: "callout", eyebrow: "One pass", text: "One agent returns all three as JSON. The next demo loops until a score is high enough." }],
        ] },
      ],
    },
    {
      title: "Multi-Turn Reflection",
      subtitle: "A meal plan: iterate until a quality threshold is met – with an upper limit on rounds",
      demo: S + "9_2_meal_plan_reflection.py",
      blocks: [
        { type: "chain", items: ["generate", "verify: score < 9", "revise", "verify: score ≥ 9", "STOP"], highlight: [4] },
        { type: "tiles", cols: 3, size: 10, titleSize: 11, items: [
          { icon: "FaCalculator", title: "Real arithmetic", text: "Python computes the targets and sums the plan's totals" },
          { icon: "FaGavel", title: "Grounded critique", text: "The LLM grades using those totals, not its own opinion" },
          { icon: "FaStop", title: "Stopping rule", text: "Score 9+ or 4 iterations, whichever comes first" },
        ] },
        { type: "text", size: 11.5, color: "slate", text: "Runs as a Streamlit app: `streamlit run 9_2_meal_plan_reflection.py`." },
      ],
    },
    {
      title: "Plan-and-Execute, Revisited",
      subtitle: "Planning decides what to do (strategy); execution does it (action)",
      demo: S + "9_3_study_plan_plan_execute.py",
      split: [1.2, 1],
      left: [
        { type: "text", text: "**Turn a 25-module curriculum PDF into a 4-week study plan for a working professional.**", size: 11.5 },
        { type: "steps", size: 10.5, titleSize: 11, gap: 0.08, items: [
          { title: "extract_curriculum", text: "Read the PDF text into the task" },
          { title: "plan_step", text: "Commit to a full ordered plan up front" },
          { title: "execute_step", text: "Work one step at a time, e.g. \"draft week 1\"" },
          { title: "replan_step", text: "Shorten, extend or reorder what remains, or finish" },
        ] },
      ],
      right: [
        { type: "icons", d: 0.42, items: [
          { icon: "FaListOl", title: "Planner", text: "Writes the numbered plan" },
          { icon: "FaPersonRunning", title: "Executor", text: "A plain LLM call – no tools are needed here" },
          { icon: "FaRoute", title: "Replanner", text: "Re-examines the plan after every step" },
        ] },
      ],
    },
    {
      title: "Replanning",
      subtitle: "Update the plan when new information arrives – during execution the agent may discover that…",
      demo: S + "9_4_pathology_report_replanning.py",
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

    // ---------------------------------------------------------------- memory
    {
      title: "Memory Types",
      subtitle: "Keep context, remember preferences, recall past work – and stop asking the same questions",
      demo: S + "9_5_agent_memory_short_term_langgraph.py → 9_6, 9_7, 9_8",
      blocks: [
        { type: "table", size: 10.5, widths: [1.9, 2.2, 1.4, 2.5], head: ["Memory type", "Purpose", "Lifetime", "Example"], rows: [
          ["Short-term (working)", "The current conversation", "Minutes / session", "Previous chat messages"],
          ["Long-term", "Persistent user knowledge", "Days to years", "Preferences, profile"],
          ["External", "Stored outside the agent", "Persistent", "ChromaDB, SQL, Redis"],
          ["Semantic", "Facts and knowledge", "Persistent", "\"Python is your preferred language\""],
          ["Episodic", "Past interactions", "Persistent", "Earlier support sessions"],
          ["Procedural", "Learned procedures", "Persistent", "How to deploy an application"],
        ] },
      ],
    },
    {
      title: "Memory Demos, in Order",
      subtitle: "Each script adds one memory capability",
      demo: S + "9_5 → 9_12",
      blocks: [
        { type: "steps", items: [
          { title: "Short-term memory", text: "`9_5_agent_memory_short_term_langgraph.py`" },
          { title: "Session ID from the user", text: "`9_6_agent_memory_dynamic_session_id_langgraph.py` – the user ID becomes the session ID" },
          { title: "Short-term → long-term", text: "`9_7_…_short_to_long_term_langgraph.py` and `9_8_…_short_to_external_sqlite_langgraph.py`" },
          { title: "The three long-term types", text: "`9_9_…_semantic`, `9_10_…_procedural` and `9_12_…_episodic_langgraph.py`" },
        ] },
      ],
    },
    {
      title: "Long-Term Memory: Three Kinds",
      subtitle: "Episodic = experiences.  Semantic = knowledge.  Procedural = skills.",
      demo: S + "9_9_agent_memory_semantic_langgraph.py, 9_10_agent_memory_procedural_langgraph.py",
      blocks: [
        { type: "cards", size: 11, items: [
          { icon: "FaClockRotateLeft", title: "Episodic", tag: "What happened?", lines: ["\"We discussed Project X last Tuesday.\""] },
          { icon: "FaBook", title: "Semantic", tag: "What do I know?", lines: ["\"Project X uses PostgreSQL.\""] },
          { icon: "FaGears", title: "Procedural", tag: "How do I do it?", lines: ["\"Deploy Project X using this procedure.\""] },
        ] },
      ],
    },
    {
      title: "Episodic Memory in Practice",
      subtitle: "Store specific past episodes outside the model and recall them when a similar case arrives",
      demo: S + "9_11_episodic_memory_store.py, 9_12_agent_memory_episodic_langgraph.py",
      blocks: [
        { type: "flow", items: [
          { icon: "FaDatabase", label: "Seed", caption: "324 past support tickets, one text blob each" },
          { icon: "FaMagnifyingGlass", label: "recall()", caption: "Find the 2 most similar episodes" },
          { icon: "FaFileLines", label: "Prompt", caption: "\"Use these similar PAST resolved cases\"" },
          { icon: "FaReply", label: "Answer", caption: "Grounded in past resolutions" },
          { icon: "FaFloppyDisk", label: "remember()", caption: "Store this Q and A as a new episode", color: "coral" },
        ] },
        { type: "code", caption: "Each episode", code: `"Customer asked: Why was my payment declined? | Resolution: ..."` },
      ],
    },
    {
      title: "Memory Consolidation",
      subtitle: "Summarise and compress old episodes before they pile up",
      demo: S + "9_13_memory_consolidation.py",
      blocks: [
        { type: "compare", size: 11, cols: [
          { title: "Without consolidation", color: "slate", items: ["Day 1 → episode 1 … day 100 → episode 100", "Large, redundant, expensive to search", "Hard to reason over"] },
          { title: "With consolidation", color: "teal", items: ["Find common patterns across episodes", "Replace each group with one dense summary", "Swap the summaries into the vector store"] },
        ] },
        { type: "chain", items: ["8 episodes", "3 patterns: 2FA issue · card declined · subscription cancellation", "3 summaries"], highlight: [2] },
      ],
    },
    {
      title: "Context Propagation and Trimming",
      subtitle: "Pass the right information forward – and keep it within the context window",
      demo: S + "9_14_context_management_strategies.py",
      split: [1, 1.25],
      left: [
        { type: "text", text: "**The same 16-message support chat, trimmed five ways:**", size: 11.5 },
        { type: "steps", size: 10.5, titleSize: 11, gap: 0.08, items: [
          { title: "Message 0 states order #ORD-88213" },
          { title: "15 later messages bury it" },
          { title: "The follow-up asks for that order number" },
          { title: "Sliding window is expected to lose it" },
        ] },
      ],
      right: [
        { type: "table", size: 10, widths: [1.6, 2.6, 1.4], head: ["Trimming strategy", "How", "Best for"], rows: [
          ["Sliding window", "Keep only the latest N messages", "Chatbots"],
          ["Summarisation", "Replace older turns with a summary", "Long conversations"],
          ["Semantic retrieval", "Pull back only relevant memories", "Long-term memory"],
          ["Token-based", "Drop the oldest content at a token limit", "Production"],
          ["Priority-based", "Always keep critical facts, drop details", "Enterprise agents"],
        ] },
      ],
    },
    {
      title: "Self-Improvement from Failures",
      subtitle: "Learn corrected facts from mistakes – good answers leave no trace, mistakes leave a lesson",
      demo: S + "9_15_self_improving_agent.py",
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
      demo: S + "9_16_personal_memory_assistant.py",
      blocks: [
        { type: "flow", loop: "the cycle repeats as the agent works", items: [
          { icon: "FaMemory", label: "Memory", caption: "What do I know?" },
          { icon: "FaListOl", label: "Planning", caption: "What should I do?" },
          { icon: "FaPersonRunning", label: "Execution", caption: "How do I act?" },
          { icon: "FaMagnifyingGlassChart", label: "Reflection", caption: "Is it working?", color: "coral" },
          { icon: "FaRoute", label: "Replanning", caption: "What should change?", color: "teal" },
        ] },
        { type: "callout", eyebrow: "In the demo", text: "A voice assistant (Whisper + LangChain memory + GPT + TTS) that recalls facts across turns. It shows the memory part; putting all five stages together is your exercise." },
      ],
    },
    {
      kind: "summary",
      title: "Session 9 and Course Summary",
      subtitle: "What you built today – and across the course",
      built: [
        { tag: "9_1", title: "Reflection loops", text: "Generate, critique and revise to a quality bar" },
        { tag: "9_4", title: "Replanning", text: "A plan that changes when a report says so" },
        { tag: "9_11", title: "Episodic memory", text: "Support tickets recalled and consolidated" },
        { tag: "9_15", title: "Self-improving agent", text: "Lessons stored only when the agent was wrong" },
        { tag: "S1–9", title: "The full journey", text: "SDK agents → LangChain → LangGraph → crews and teams → agentic RAG → deep agents" },
      ],
      takeaways: [
        "Deep agents evaluate how they are doing, not just what to do",
        "Reflection needs a rubric and a stopping rule",
        "Plan up front for long tasks; replan when facts change",
        "Choose the memory type by what must be remembered",
        "Trim context deliberately – the window is a budget",
      ],
      next: "Thank you! Keep building – the code is at github.com/atulkahatecdac/agenticai",
    },
  ],
};
