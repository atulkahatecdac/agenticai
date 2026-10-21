const M = "08_langgraph_cycles_HIL_persistence/";

module.exports = {
  section: "Module 08 – LangGraph Cycles, HIL, Persistence",
  slides: [
    {
      kind: "opener",
      eyebrow: "Module 08",
      title: "LangGraph: Cycles, HIL and Persistence",
      subtitle: "Graphs that loop until the work is done, pause for a human, survive a crash, and fan out in parallel",
      goals: [
        { icon: "FaArrowsRotate", title: "Build loops with a safe exit", text: "conditional edges back to an earlier node" },
        { icon: "FaUserCheck", title: "Pause for human approval", text: "interrupts and resuming a paused graph" },
        { icon: "FaFloppyDisk", title: "Persist and recover state", text: "SQLite and Redis checkpointers, thread IDs" },
        { icon: "FaSitemap", title: "Scale the structure", text: "Send API for parallel work; subgraphs" },
      ],
      agenda: [
        "Cycles and loops",
        "Human-in-the-loop",
        "Checkpointers and crash recovery",
        "Production persistence with Redis",
        "Parallel work with the Send API",
        "Subgraphs",
      ],
    },
    {
      title: "Cycles: An Order-Processing State Machine",
      subtitle: "A graph that can return to a node it already ran – here, to retry a payment",
      demo: M + "order_processing_state_machine.py",
      split: [1.1, 1],
      left: [
        { type: "table", size: 10, widths: [1.5, 1.2, 1.7], head: ["From", "Label", "To"], rows: [
          ["check_inventory", "in_stock", "process_payment"],
          ["check_inventory", "out_of_stock", "fail_order"],
          ["process_payment", "approved", "ship_order"],
          ["process_payment", "**retry**", "**process_payment ↺**"],
          ["process_payment", "give_up", "fail_order"],
          ["ship_order / fail_order", "", "notify_customer (LLM) → END"],
        ] },
      ],
      right: [
        { type: "text", text: "**Loops appear whenever work must be repeated**", size: 11.5 },
        { type: "bullets", size: 11, items: [
          "Search until enough documents are found",
          "Retry failed API calls",
          "Improve generated code",
          "Refine an answer until it passes a check",
        ] },
        { type: "callout", eyebrow: "How", text: "A loop is just a conditional edge that points back to an earlier node." },
      ],
    },
    {
      title: "Creating the Loop",
      subtitle: "The routing function reads the state and returns a label; the map turns labels into nodes",
      demo: M + "order_processing_state_machine.py",
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
      demo: M + "human_approval_gate.py",
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
        { type: "tree", boxW: 1.6, size: 10, boxH: 0.34, gapY: 0.22, rows: [["Node"], [{ label: "PAUSE – human reviews", fill: "coral" }], ["Approve / reject / modify"], [{ label: "Continue", fill: "teal" }]] },
      ],
    },

    // ---------------------------------------------------------------- persistence
    {
      title: "Checkpointers",
      subtitle: "Save the graph's state so execution can continue later instead of starting over",
      demo: M + "sqlite_checkpointing_crash_recovery.py",
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
      ],
    },
    {
      title: "Crash Recovery with a SQLite Checkpointer",
      subtitle: "A bank transfer that crashes half-way, then resumes exactly where it stopped",
      demo: M + "sqlite_checkpointing_crash_recovery.py",
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
              "It runs only credit_account – attempt 2 succeeds, and the debit is not repeated",
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
      title: "Production Persistence with Redis",
      subtitle: "A .sqlite file belongs to one machine; a scaled-out app needs a shared checkpoint store",
      demo: M + "redis_checkpointing_production.py  (needs Redis on REDIS_URL)",
      split: [1, 1.1],
      left: [
        { type: "compare", size: 10.5, cols: [
          { title: "SqliteSaver", color: "slate", items: ["Local file, one process", "Ready to use at once", "Rows kept forever"] },
          { title: "RedisSaver", color: "teal", items: ["Network service shared by every instance", "Any instance can resume any thread", "TTL – old checkpoints expire"] },
        ] },
      ],
      right: [
        { type: "code", caption: "redis_checkpointing_production.py (condensed)", code:
`from langgraph.checkpoint.redis import RedisSaver

TTL = {"default_ttl": 60, "refresh_on_read": True}

with RedisSaver.from_conn_string(REDIS_URL, ttl=TTL) as cp:
    cp.setup()              # create the search indices
    app = graph.compile(checkpointer=cp)
    app.invoke(state, config)   # run 1 crashes

# run 2: a fresh connection – as another instance would
with RedisSaver.from_conn_string(REDIS_URL, ttl=TTL) as cp:
    cp.setup()
    app = graph.compile(checkpointer=cp)
    app.invoke(None, config)    # resumes the thread` },
      ],
    },
    { kind: "image", src: "langgraph_memory_options.png", alt: "LangGraph memory options: no memory, MemorySaver, SqliteSaver", demo: "../3_langgraph/3_4_langgraph_memory.py" },

    // ---------------------------------------------------------------- structure
    {
      title: "Parallel Work with the Send API",
      subtitle: "Run the same node many times at once, each copy with its own input",
      demo: M + "parallel_trip_planner_send_api.py",
      split: [1, 1.15],
      left: [
        { type: "tree", boxW: 1.05, size: 9.5, boxH: 0.36, rows: [["Choose a country"], ["Find 4 cities"], ["Flights", "City 1", "City 2", "City 3", "City 4"], [{ label: "Final summary", fill: "teal" }]] },
        { type: "text", size: 11, color: "slate", text: "Also good for: summarising many documents, screening resumes, analysing reviews, processing images." },
      ],
      right: [
        { type: "code", caption: "Return a list of Send objects instead of one node name", code:
`def dispatch_research(state) -> list[Send]:
    sends = [Send("search_flights", {
        "arrival_airport_iata": state["arrival_airport_iata"],
        "start_date": state["start_date"],
        "end_date": state["end_date"]})]
    for city in state["cities"]:
        sends.append(Send("research_city", {
            "city": city,
            "start_date": state["start_date"],
            "end_date": state["end_date"]}))
    return sends

graph.add_conditional_edges("determine_cities",
    dispatch_research, ["search_flights", "research_city"])` },
      ],
    },
    {
      title: "Subgraphs",
      subtitle: "A graph inside a graph – split one huge workflow into smaller, reusable pieces",
      demo: M + "simple_subgraph_example.py, medical_diagnosis_subgraphs.py",
      blocks: [
        { type: "chain", items: ["medical_history (subgraph)", "lab_analysis (subgraph)", "analyze_xray", "diagnosis", "prescription"], highlight: [0, 1] },
        { type: "text", size: 11, color: "slate", text: "Each subgraph has its own state and nodes – e.g. lab_analysis runs load_lab_results → flag_abnormal_results → summarize_labs – and is called from one node of the main graph." },
        { type: "tiles", cols: 3, items: [
          { icon: "FaPuzzlePiece", title: "One responsibility each", text: "A subgraph does one well-defined job" },
          { icon: "FaRecycle", title: "Reusable", text: "Plug the same subgraph into other graphs" },
          { icon: "FaMagnifyingGlass", title: "Easier to test", text: "Debug a piece without running everything" },
        ] },
      ],
    },
    {
      kind: "summary",
      title: "Module 08 Summary",
      subtitle: "What you built",
      built: [
        { tag: "loop", title: "A retrying state machine", text: "Payment retries with a give-up exit" },
        { tag: "HITL", title: "Human approval gate", text: "interrupt() and resume for expense claims" },
        { tag: "ckpt", title: "Crash recovery", text: "SQLite locally, Redis in production" },
        { tag: "Send", title: "Parallel research", text: "Flights and four cities at once" },
        { tag: "sub", title: "Subgraphs", text: "A medical-diagnosis flow from smaller graphs" },
      ],
      takeaways: [
        "A loop is a conditional edge pointing backwards – add an exit",
        "Human-in-the-loop needs a checkpointer",
        "thread_id picks which saved run to continue",
        "Use a shared store (Redis) once you scale out",
        "Send fans out; subgraphs keep big graphs manageable",
      ],
      next: "Module 09: LangSmith",
    },
  ],
};
