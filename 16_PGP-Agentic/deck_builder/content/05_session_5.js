const S = "session_5/";

module.exports = {
  section: "Session 5 – LangGraph Cycles, HITL, Persistence",
  slides: [
    {
      kind: "opener",
      eyebrow: "Session 5  ·  Sun 7-Nov  ·  08:00–11:00 AM",
      title: "LangGraph: Cycles, Human-in-the-Loop and Persistence",
      subtitle: "Graphs that loop until the work is good enough, pause for a human, and survive a crash",
      goals: [
        { icon: "FaArrowsRotate", title: "Build loops with a safe exit", text: "conditional edges back to an earlier node, with a limit" },
        { icon: "FaUserCheck", title: "Pause for human approval", text: "interrupt() and resume with Command(resume=…)" },
        { icon: "FaFloppyDisk", title: "Persist and recover state", text: "checkpointers, thread IDs, SQLite crash recovery" },
        { icon: "FaShieldHalved", title: "Structure and protect the graph", text: "state schema design, subgraphs, guardrails" },
      ],
      agenda: [
        "Cycles and loops",
        "Human-in-the-loop (HITL)",
        "Checkpointers and persistence",
        "State schema design",
        "Subgraphs",
        "Guardrails in LangGraph",
        "End-to-end: stateful banking chatbot",
      ],
    },
    {
      title: "Loops in LangGraph",
      subtitle: "A node can run more than once – here, an answer is refined until the evaluator is satisfied",
      demo: S + "5_1_langgraph_looping_agents.py",
      split: [1.15, 1],
      left: [
        { type: "flow", loop: "continue → back to answer", items: [
          { icon: "FaPen", label: "answer", caption: "Ask the LLM to answer or improve; iterations + 1" },
          { icon: "FaScaleBalanced", label: "evaluate", caption: "Ask the LLM: continue or stop?" },
          { icon: "FaCodeBranch", label: "should_continue", caption: "Stop if iterations ≥ 3, else use the decision", color: "coral" },
        ] },
      ],
      right: [
        { type: "code", caption: "The loop is just a conditional edge", code:
`class AgentState(TypedDict):
    question: str
    answer: str
    history: List[str]
    iterations: int
    decision: str   # "continue" | "stop"

builder.add_conditional_edges(
    "evaluate",
    should_continue,
    {"continue": "answer",   # LOOP
     "stop": END},           # EXIT
)` },
      ],
    },
    {
      title: "Retry Loops in a Workflow",
      subtitle: "An order-processing state machine: approve, retry the payment, or give up",
      demo: S + "5_2_langgraph_code_review.py, 5_3_order_processing_state_machine.py",
      split: [1, 1.1],
      left: [
        { type: "code", caption: "Routing after payment", code:
`graph.add_conditional_edges(
    "process_payment",        # source node
    route_after_payment,      # routing function
    {
        "approved": "ship_order",
        "retry":    "process_payment",   # loop
        "give_up":  "fail_order",
    },
)` },
      ],
      right: [
        { type: "icons", d: 0.38, size: 11, items: [
          { icon: "FaCircleCheck", title: "approved", text: "Continue to ship_order", color: "teal" },
          { icon: "FaRotateRight", title: "retry", text: "Go back to process_payment – this is the cycle", color: "coral" },
          { icon: "FaCircleXmark", title: "give_up", text: "Stop at fail_order after too many attempts", color: "slate" },
        ] },
        { type: "callout", eyebrow: "Always", text: "Give every loop an exit: an attempt counter, a quality threshold, or both." },
      ],
    },

    // ---------------------------------------------------------------- HITL
    {
      title: "Human-in-the-Loop",
      subtitle: "Pause the graph at a risky step so a person can approve, edit or reject before it continues",
      demo: S + "5_4_human_approval_gate.py, 5_5_support_ticketing_agent_hitl.py, 5_6_…_memory_rag.py",
      split: [1.15, 1],
      left: [
        { type: "flow", items: [
          { icon: "FaReceipt", label: "evaluate_expense", caption: "LLM assesses the claim" },
          { icon: "FaHand", label: "human_approval", caption: "interrupt(…) pauses here", color: "coral" },
          { icon: "FaPlay", label: "Resume", caption: "invoke(Command(resume=decision))", color: "teal" },
        ] },
        { type: "bullets", size: 11, items: [
          "`interrupt()` returns control to the caller with a payload to show the human",
          "The state is saved by the checkpointer – a checkpointer is **required**",
          "Static alternative: `interrupt_before` / `interrupt_after` a named node",
        ] },
      ],
      right: [
        { type: "text", text: "**Where it's needed:** loan approvals, large transfers, medical recommendations, legal documents, contract signing", size: 11.5 },
        { type: "callout", eyebrow: "A good HITL screen shows", text: "The AI's recommendation · supporting evidence and retrieved documents · a confidence score · a short reasoning summary · clear action buttons" },
      ],
    },

    // ---------------------------------------------------------------- persistence
    {
      title: "Checkpointers",
      subtitle: "Save the graph's state so execution can continue later instead of starting over",
      demo: S + "5_7_langgraph_memory.py, 5_8_sqlite_checkpointing_crash_recovery.py",
      blocks: [
        { type: "tiles", cols: 3, items: [
          { icon: "FaDatabase", title: "Graph state", text: "All current field values" },
          { icon: "FaLocationCrosshairs", title: "Current node", text: "Where execution stopped" },
          { icon: "FaComments", title: "Conversation history", text: "Messages so far" },
          { icon: "FaHashtag", title: "Thread ID", text: "Which run this state belongs to" },
          { icon: "FaPause", title: "Pending interrupts", text: "What the human must answer" },
          { icon: "FaListCheck", title: "Variables", text: "Counters, flags, results" },
        ] },
        { type: "compare", size: 11, cols: [
          { title: "Without persistence", color: "slate", items: ["Graph → state → RAM → program ends → **lost**"] },
          { title: "With persistence", color: "teal", items: ["Graph → state → SQLite → program ends → **retained**"] },
        ] },
        { type: "text", size: 11.5, color: "slate", text: "**Checkpointer ≠ memory.** A checkpointer answers \"where was the agent?\"; memory answers \"what does the agent know?\"" },
      ],
    },
    {
      title: "Crash Recovery with a SQLite Checkpointer",
      subtitle: "A bank transfer that crashes half-way, then resumes exactly where it stopped",
      demo: S + "5_8_sqlite_checkpointing_crash_recovery.py",
      blocks: [
        { type: "flow", items: [
          { icon: "FaPlay", label: "START", caption: "thread_id = \"transfer-1\"" },
          { icon: "FaMinus", label: "debit_account", caption: "$250 debited" },
          { icon: "FaFloppyDisk", label: "Checkpoint", caption: "Saved to SQLite", color: "teal" },
          { icon: "FaBurst", label: "credit_account", caption: "Deliberate crash on attempt 1", color: "coral" },
        ] },
        { type: "cols", ratio: [1, 1.15], cols: [
          [
            { type: "text", text: "**Run 2 – resume from disk**", size: 12.5 },
            { type: "bullets", size: 11, items: [
              "`app.invoke(None, config)` – None means \"don't start fresh; resume this thread\"",
              "LangGraph finds transfer-1 with debit_account already completed",
              "It runs only credit_account – the second attempt succeeds, and the debit is not repeated",
            ] },
          ],
          [
            { type: "code", caption: "What the checkpoint holds for transfer-1", code:
`{
  "amount": 250.00,
  "completed_steps": ["debit_account"]
}
# next node to run: credit_account` },
          ],
        ] },
      ],
    },
    {
      title: "Designing the State Schema",
      subtitle: "State is everything the agent needs while it works – each node reads it and adds to it",
      demo: S + "5_9_langgraph_reducer_return_policy.py",
      split: [1, 1.2],
      left: [
        { type: "table", size: 10.5, widths: [1.4, 2.2], head: ["Field", "Holds"], rows: [
          ["messages", "Conversation history"],
          ["user_query", "The current request"],
          ["retrieved_docs", "Knowledge found by retrieval"],
          ["tool_results", "Results returned by tools"],
          ["reasoning", "Intermediate reasoning"],
          ["final_answer", "The response"],
          ["user_profile", "Preferences and profile"],
          ["status", "Where the workflow is"],
        ] },
      ],
      right: [
        { type: "text", text: "**\"Am I eligible for a ₹50 lakh home loan?\"** – the state fills up as the graph runs:", size: 11.5 },
        { type: "steps", size: 10.5, titleSize: 11.5, gap: 0.08, items: [
          { title: "Initial", text: "messages, user_query" },
          { title: "After retrieval", text: "+ retrieved_docs" },
          { title: "After tool execution", text: "+ tool_results" },
          { title: "After reasoning", text: "+ reasoning" },
          { title: "Final", text: "+ final_answer" },
        ] },
      ],
    },
    {
      title: "Subgraphs",
      subtitle: "A graph inside a graph – split one huge workflow into smaller, reusable pieces",
      demo: S + "5_10_simple_subgraph_example.py, 5_11_medical_diagnosis_subgraphs.py",
      blocks: [
        { type: "chain", items: ["medical_history (subgraph)", "lab_analysis (subgraph)", "analyze_xray", "diagnosis", "prescription"], highlight: [0, 1] },
        { type: "text", size: 11, color: "slate", text: "In 5_11, each subgraph has its own state and nodes – e.g. lab_analysis runs load_lab_results → flag_abnormal_results → summarize_labs – and is called from one node of the main graph." },
        { type: "tiles", cols: 3, items: [
          { icon: "FaPuzzlePiece", title: "One responsibility each", text: "A subgraph does one well-defined job" },
          { icon: "FaRecycle", title: "Reusable", text: "Plug the same subgraph into other graphs" },
          { icon: "FaMagnifyingGlass", title: "Easier to test", text: "Debug a piece without running everything" },
        ] },
      ],
    },

    // ---------------------------------------------------------------- guardrails
    { kind: "image", src: "guardrails_in_agents.png", alt: "Guardrails in AI agents", demo: S + "5_12_…_create_guardrails.py, 5_13_…_test_guardrails_flask.py, 5_14_…_bank_flask.py" },
    {
      title: "Types of Guardrails",
      subtitle: "Controls that keep a model within limits: safe, on-topic, accurate and within policy",
      demo: S + "5_12_…_create_guardrails.py, 5_13_…_test_guardrails_flask.py, 5_14_…_bank_flask.py",
      blocks: [
        { type: "tiles", cols: 3, size: 10, items: [
          { icon: "FaBan", title: "Keyword blocking", text: "Block restricted words" },
          { icon: "FaFilter", title: "Input validation", text: "Max length, no URLs or code" },
          { icon: "FaListCheck", title: "Allow-listed topics", text: "Only product questions, say" },
          { icon: "FaBrain", title: "Semantic safety", text: "Embedding similarity to harmful intent" },
          { icon: "FaComment", title: "Prompt guardrails", text: "\"Use the context only\"" },
          { icon: "FaEraser", title: "Output filtering", text: "Strip sensitive data, profanity" },
          { icon: "FaScrewdriverWrench", title: "Tool-use limits", text: "No web search for medical queries" },
          { icon: "FaGaugeHigh", title: "Rate and abuse control", text: "Throttling, authentication" },
          { icon: "FaBookOpen", title: "Grounding", text: "Retrieval-only answers with citations" },
        ] },
        { type: "text", size: 11, color: "slate", text: "The demos build a semantic guardrail from a Hugging Face dataset (5_12), test it (5_13), then put it in front of the bank chatbot (5_14)." },
      ],
    },
    {
      title: "End to End: The Stateful Banking Chatbot",
      subtitle: "The bank assistant grows feature by feature across these scripts",
      demo: S + "5_15_…_chromadb_flask_chatbot.py, 5_16_…_ntfy_email_flask.py, 5_17_…_STM_RAG_chatbot.py",
      blocks: [
        { type: "flow", items: [
          { icon: "FaDatabase", label: "5_15  RAG chatbot", caption: "Bank FAQs in ChromaDB, Flask UI" },
          { icon: "FaBell", label: "5_16  Notifications", caption: "ntfy.sh alerts and Gmail for escalations" },
          { icon: "FaShieldHalved", label: "5_14  Guardrails", caption: "Unsafe questions never reach the LLM" },
          { icon: "FaMemory", label: "5_17  STM + RAG", caption: "Check short-term memory first, then the vector DB" },
        ] },
        { type: "callout", eyebrow: "Try it", text: "Run 5_15 and ask a few banking questions; then 5_16 to see an escalation reach your phone (ntfy) and inbox; then 5_14 and try an off-topic or unsafe question." },
      ],
    },
    {
      kind: "summary",
      title: "Session 5 Summary",
      subtitle: "What you built today",
      built: [
        { tag: "5_1", title: "A self-refining loop", text: "answer → evaluate → continue or stop, capped at 3 rounds" },
        { tag: "5_4", title: "Human approval gate", text: "interrupt() and Command(resume=…) for expense claims" },
        { tag: "5_8", title: "Crash recovery", text: "A SQLite checkpointer resumes a half-done transfer" },
        { tag: "5_11", title: "Subgraphs", text: "A medical-diagnosis flow built from smaller graphs" },
        { tag: "5_14", title: "Guarded bank bot", text: "Semantic guardrails in front of RAG" },
      ],
      takeaways: [
        "A loop is a conditional edge pointing backwards – always add an exit",
        "Human-in-the-loop needs a checkpointer to pause and resume",
        "thread_id is how you pick which saved run to continue",
        "Design state fields before writing nodes",
        "Guardrails belong on input, output and tool use",
      ],
      next: "Session 6: Multi-Agent Orchestration with CrewAI",
    },
  ],
};
