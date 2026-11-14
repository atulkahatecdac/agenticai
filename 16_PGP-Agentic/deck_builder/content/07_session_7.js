const S = "session_7/";

module.exports = {
  section: "Session 7 – Microsoft Agent Framework and AutoGen",
  slides: [
    {
      kind: "opener",
      eyebrow: "Session 7",
      title: "Microsoft Agent Framework and AutoGen",
      subtitle: "Build a SecureBank support desk with Microsoft's agent framework – then migrate the AutoGen code it replaces",
      goals: [
        { icon: "FaRobot", title: "Build safe agents", text: "tools, sessions, middleware, human approval" },
        { icon: "FaDiagramProject", title: "Orchestrate with workflows", text: "routing, parallel checks, checkpoints, handoffs" },
        { icon: "FaChartLine", title: "See what agents do", text: "OpenTelemetry traces for every LLM and tool call" },
        { icon: "FaRightLeft", title: "Migrate AutoGen code", text: "AgentChat teams and GraphFlow → Agent Framework" },
      ],
      agenda: [
        "What is Microsoft Agent Framework (MAF)?",
        "Agents: tools, sessions, structured output",
        "Middleware and human approval",
        "Workflows: routing, parallel checks, checkpoints",
        "Orchestrations: sequential, concurrent, handoff",
        "Observability",
        "AutoGen AgentChat and migrating to MAF",
      ],
    },
    {
      title: "What is Microsoft Agent Framework?",
      subtitle: "One open-source SDK (Python and .NET) that replaces both AutoGen and Semantic Kernel",
      demo: "Concept",
      blocks: [
        { type: "flow", items: [
          { icon: "FaComments", label: "AutoGen", caption: "Multi-agent conversations – research project, now in maintenance mode" },
          { icon: "FaBuilding", label: "Semantic Kernel", caption: "Enterprise features: sessions, telemetry, filters" },
          { icon: "FaCubes", label: "Agent Framework", caption: "Both merged into one SDK – 1.0 GA in April 2026", color: "coral" },
        ] },
        { type: "cards", size: 10, items: [
          { icon: "FaRobot", title: "Agents", tag: "LLM decides", lines: ["`Agent(client, instructions, tools)` – one class for every provider", "Sessions, middleware, approvals, MCP tools"] },
          { icon: "FaDiagramProject", title: "Workflows", tag: "You decide", lines: ["Typed graph of agents and functions: edges, switch-case, fan-out/in", "Checkpoints, human-in-the-loop, ready-made orchestrations"] },
          { icon: "FaPlug", title: "Clients", tag: "Swap the LLM", lines: ["OpenAI, Azure, Anthropic, Ollama, Gemini …", "Each a small `agent-framework-*` package"] },
        ] },
      ],
    },
    {
      title: "Where MAF Fits",
      subtitle: "You already know LangGraph and CrewAI – when would you pick the Agent Framework?",
      demo: "Concept",
      blocks: [
        { type: "table", size: 10, widths: [1.5, 2, 2, 2.2], head: ["", "LangGraph", "CrewAI", "Agent Framework"], rows: [
          ["Mental model", "State machine over a shared state dict", "A crew of role-playing agents with tasks", "Agents + typed message-passing workflows"],
          ["Control flow", "Nodes, edges, conditional edges", "Sequential or hierarchical process; Flows", "Edges, switch-case, fan-out/in; 5 built-in orchestrations"],
          ["Human-in-the-loop", "`interrupt()` + checkpointer", "`human_input=True` on a task", "Tool approval + request/response events"],
          ["Enterprise extras", "LangSmith tracing", "Enterprise platform", "Middleware, OpenTelemetry, Azure/Foundry hosting, .NET"],
          ["Pick it when", "You want fine control of state", "You think in roles and tasks", "You're on Microsoft's stack or need policy + telemetry built in"],
        ] },
      ],
    },
    {
      title: "Today's Build: The SecureBank Support Desk",
      subtitle: "Every MAF demo adds one piece to the same banking app",
      demo: S + "7_1_* … 7_9_*",
      blocks: [
        { type: "cols", cols: [
          [{ type: "table", size: 10, widths: [3.3, 0.8], head: ["Agents – what it adds", "Script"], rows: [
            ["Assistant with balance and live FX tools", "7_1"],
            ["Remembers the customer; complaint → ticket", "7_2"],
            ["Masks card numbers, audits and blocks tools", "7_3"],
            ["Asks a human before moving money", "7_4"],
            ["Traces every LLM and tool call", "7_9"],
          ] }],
          [{ type: "table", size: 10, widths: [3.3, 0.8], head: ["Workflows – what it adds", "Script"], rows: [
            ["Routes requests to the right desk", "7_5"],
            ["Loan checks in parallel, resumable", "7_6"],
            ["Campaign review: sequential and concurrent", "7_7"],
            ["Live desk where agents hand off the chat", "7_8"],
          ] }],
        ] },
        { type: "callout", eyebrow: "Install", text: "pip install agent-framework-core agent-framework-openai agent-framework-orchestrations (all pinned in requirements.txt)" },
      ],
    },
    {
      title: "MAF: An Agent with Tools",
      subtitle: "A plain Python function becomes a tool with @tool; run() returns a reply, run(stream=True) streams it",
      demo: S + "7_1_maf_bank_assistant.py",
      split: [1.2, 1],
      left: [
        { type: "code", caption: "7_1_maf_bank_assistant.py (condensed)", code:
`@tool
def get_balance(account_id: str) -> str:
    """Return the owner and balance of an account."""
    ...

agent = Agent(
    OpenAIChatCompletionClient(model="gpt-4o-mini"),
    name="bank_assistant",
    instructions="You are SecureBank's assistant. ...",
    tools=[get_balance, get_forex_rate],
)

result = await agent.run("What is the balance of ACC-1001?")
print(result.text)

stream = agent.run("ACC-1001's balance in USD?", stream=True)
async for update in stream:
    print(update.text, end="")` },
      ],
      right: [
        { type: "table", size: 10, widths: [1.5, 2.6], head: ["Piece", "What it does"], rows: [
          ["`Agent`", "One class for every LLM provider"],
          ["client", "First argument – the only provider-specific line"],
          ["`instructions`", "The system prompt"],
          ["`@tool`", "Docstring + type hints become the tool schema"],
          ["`run()`", "Calls tools as needed – here two in one question"],
          ["`stream=True`", "Same call, yields updates as they arrive"],
        ] },
      ],
    },
    {
      title: "MAF: Sessions and Structured Output",
      subtitle: "Agents are stateless – memory lives in a session you pass in; a Pydantic model shapes the reply",
      demo: S + "7_2_maf_session_and_structured_output.py",
      blocks: [
        { type: "compare", size: 11, codeSize: 9, cols: [
          { title: "Session = memory", color: "navy", items: ["Without a session every run starts from scratch", "Pass the same session to keep the history"], code:
`session = agent.create_session()
await agent.run("Hi, I'm Priya, account ACC-1001",
                session=session)
await agent.run("Which account did I mention?",
                session=session)` },
          { title: "Complaint → support ticket", color: "teal", items: ["Free text in, typed object out", "`result.value` is a ready-made SupportTicket"], code:
`class SupportTicket(BaseModel):
    category: Literal["cards", "loans", "fraud", ...]
    urgency: Literal["low", "medium", "high"]
    account_id: str | None
    summary: str

result = await agent.run(complaint,
    options={"response_format": SupportTicket})
ticket = result.value` },
        ] },
      ],
    },
    {
      title: "MAF: Middleware",
      subtitle: "Policy in one place, not in every prompt – code that wraps each agent run or each tool call",
      demo: S + "7_3_maf_middleware.py",
      split: [1.25, 1],
      left: [
        { type: "code", caption: "7_3_maf_middleware.py (condensed)", code:
`@agent_middleware                # around the whole run
async def mask_card_numbers(context, call_next):
    # 4111 1111 1111 1234 -> ****1234 in user messages
    ...
    await call_next()

@function_middleware             # around every tool call
async def block_risky_tools(context, call_next):
    if context.function.name == "close_account":
        context.result = "Refused by SecureBank policy ..."
        return                   # tool never runs
    await call_next()

agent = Agent(client, ..., tools=[...],
    middleware=[mask_card_numbers, audit_log,
                block_risky_tools])` },
      ],
      right: [
        { type: "icons", d: 0.36, size: 11, items: [
          { icon: "FaMask", title: "Mask PII", text: "Card numbers never reach the LLM or its logs" },
          { icon: "FaClipboardList", title: "Audit", text: "Every tool call logged with arguments, result and timing" },
          { icon: "FaBan", title: "Block", text: "Skip `call_next()` and the tool never runs – whatever the LLM asked for" },
          { icon: "FaLayerGroup", title: "Like web middleware", text: "Chain of functions; each can inspect, change or stop the call" },
        ] },
      ],
    },
    {
      title: "MAF: Human Approval Before Money Moves",
      subtitle: "approval_mode=\"always_require\" pauses the agent and hands the decision to a person",
      demo: S + "7_4_maf_tool_approval.py",
      split: [1.25, 1],
      left: [
        { type: "code", caption: "7_4_maf_tool_approval.py (condensed)", code:
`@tool(approval_mode="always_require")
def transfer_funds(from_account: str, to_account: str,
                   amount: float) -> str: ...

session = agent.create_session()
result = await agent.run(request, session=session)
while result.user_input_requests:
    answers = []
    for req in result.user_input_requests:
        call = req.function_call
        ok = input(f"Approve {call.name}?") == "y"
        answers.append(Message("user",
            [req.to_function_approval_response(ok)]))
    result = await agent.run(answers, session=session)` },
      ],
      right: [
        { type: "flow", items: [
          { icon: "FaUser", label: "Request", caption: "\"Transfer 5000 to ACC-1002\"" },
          { icon: "FaPause", label: "Pause", caption: "The run returns an approval request", color: "coral" },
          { icon: "FaUserCheck", label: "Human", caption: "Approves or rejects the exact call" },
          { icon: "FaPlay", label: "Resume", caption: "Same session – the agent finishes" },
        ] },
        { type: "text", size: 11, color: "slate", text: "Read-only tools (`get_balance`) still run without asking." },
      ],
    },
    {
      title: "MAF Workflows: The Building Blocks",
      subtitle: "When you – not the LLM – should own the order of steps",
      demo: "Concept",
      blocks: [
        { type: "cards", size: 10, items: [
          { icon: "FaGears", title: "Executors", tag: "Nodes", lines: ["Agents, or plain functions with `@executor`", "Each handles specific message types"] },
          { icon: "FaArrowRightLong", title: "Edges", tag: "Wiring", lines: ["Plain, switch-case (routing), fan-out and fan-in", "`add_edge(a, b)` and friends"] },
          { icon: "FaLayerGroup", title: "Supersteps", tag: "Execution", lines: ["Everything ready runs in parallel, then the next step", "A checkpoint can be saved after each one"] },
          { icon: "FaBolt", title: "Events", tag: "Visibility", lines: ["`executor_invoked`, `output`, `request_info` …", "Stream them with `run(..., stream=True)`"] },
        ] },
        { type: "callout", eyebrow: "Checked before it runs", text: "build() verifies that every edge connects compatible message types – a wiring mistake fails at build time, not halfway through a customer request." },
      ],
    },
    {
      title: "Workflow: Route Each Request",
      subtitle: "The LLM only classifies; a switch-case edge – plain Python – picks the desk",
      demo: S + "7_5_maf_workflow_routing.py",
      split: [1.3, 1],
      left: [
        { type: "code", caption: "7_5_maf_workflow_routing.py (condensed)", code:
`@executor(id="triage")
async def triage(text: str, ctx: WorkflowContext[...]):
    decision = (await classifier.run(text)).value
    message = Message("user", [text], additional_properties=
                      {"department": decision.department})
    await ctx.send_message(AgentExecutorRequest([message]))

workflow = (
    WorkflowBuilder(start_executor=triage, output_from=[...])
    .add_switch_case_edge_group(triage, [
        Case(condition=department_is("cards"), target=cards),
        Case(condition=department_is("loans"), target=loans),
        Case(condition=department_is("fraud"), target=fraud),
        Default(target=general),
    ])
    .build())` },
      ],
      right: [
        { type: "tree", rows: [
          [{ label: "triage", caption: "classifier agent → label" }],
          [{ label: "cards" }, { label: "loans" }, { label: "fraud" }, { label: "general" }],
        ] },
        { type: "text", size: 11, color: "slate", text: "Routing is testable and auditable: the same label always goes to the same desk." },
      ],
    },
    {
      title: "Workflow: Parallel Loan Checks with Checkpoints",
      subtitle: "Credit and fraud checks run together; state is saved after every step so a run can resume",
      demo: S + "7_6_maf_loan_pipeline_checkpoints.py",
      split: [1.3, 1],
      left: [
        { type: "code", caption: "7_6_maf_loan_pipeline_checkpoints.py (condensed)", code:
`storage = FileCheckpointStorage(CHECKPOINT_DIR)
workflow = (
    WorkflowBuilder(start_executor=intake,
        output_from=[loan_decision], checkpoint_storage=storage)
    .add_fan_out_edges(intake, [credit_officer, fraud_analyst])
    .add_fan_in_edges([credit_officer, fraud_analyst],
                      merge_checks)
    .add_edge(merge_checks, loan_decision)
    .build())

await workflow.run(APPLICATION)
checkpoints = await storage.list_checkpoints(
    workflow_name=workflow.name)

# later, even in a new process:
fresh = build_workflow(storage)
await fresh.run(checkpoint_id=cp.checkpoint_id)` },
      ],
      right: [
        { type: "tree", rows: [
          [{ label: "intake" }],
          [{ label: "credit_officer", caption: "get_credit_score" }, { label: "fraud_analyst", caption: "check_fraud_flags" }],
          [{ label: "merge_checks" }],
        ] },
        { type: "text", size: 11, color: "slate", text: "Resuming from the checkpoint after the checks runs only merge → decision – the checks are not paid for twice." },
      ],
    },
    {
      title: "Ready-Made Orchestrations",
      subtitle: "Common multi-agent patterns, one builder each – no edges to wire",
      demo: S + "7_7_maf_sequential_concurrent.py",
      split: [1.15, 1],
      left: [
        { type: "table", size: 10, widths: [2.1, 2.4], head: ["Builder", "Pattern"], rows: [
          ["`SequentialBuilder`", "Fixed order; each agent sees what came before"],
          ["`ConcurrentBuilder`", "Same input to all, in parallel; results collected"],
          ["`GroupChatBuilder`", "Orchestrator picks who speaks next (7_13)"],
          ["`HandoffBuilder`", "Agents pass the conversation to each other (7_8)"],
          ["`MagenticBuilder`", "A manager plans and delegates open-ended tasks"],
        ] },
      ],
      right: [
        { type: "code", caption: "7_7_maf_sequential_concurrent.py (condensed)", code:
`# SMS campaign: draft, then compliance rewrite
sequential = SequentialBuilder(
    participants=[copywriter, compliance]).build()

# product idea reviewed by three experts at once
concurrent = ConcurrentBuilder(
    participants=[risk, legal, customer]).build()

result = await concurrent.run(
    "Zero-fee student credit card ...")` },
      ],
    },
    {
      title: "Handoff: A Live Support Desk",
      subtitle: "Agents decide who owns the conversation – the workflow pauses whenever a human is needed",
      demo: S + "7_8_maf_handoff_support_desk.py",
      split: [1.45, 1],
      left: [
        { type: "code", caption: "7_8_maf_handoff_support_desk.py (condensed)", code:
`workflow = (HandoffBuilder(name="securebank_desk",
                participants=[triage, cards_desk, loans_desk])
            .with_start_agent(triage).build())

pending = show([e async for e in workflow.run(first, stream=True)])
while pending:
    responses = {}
    for req in pending:
        if isinstance(req.data, HandoffAgentUserRequest):
            text = input("You: ")
            reply = HandoffAgentUserRequest.create_response(text)
        else:   # approval for block_card
            reply = req.data.to_function_approval_response(ok)
        responses[req.request_id] = reply
    events = workflow.run(responses=responses, stream=True)
    pending = show([e async for e in events])` },
      ],
      right: [
        { type: "icons", d: 0.36, size: 11, items: [
          { icon: "FaRightLeft", title: "Handoff = a tool call", text: "The builder gives each agent hidden handoff tools" },
          { icon: "FaUserClock", title: "request_info events", text: "Customer reply needed, or a tool approval – both pause the run" },
          { icon: "FaCodeCompare", title: "vs 7_5 routing", text: "7_5: code routes once. 7_8: agents keep deciding, turn by turn" },
        ] },
      ],
    },
    {
      title: "Observability: Trace Every Step",
      subtitle: "Agents are already instrumented with OpenTelemetry – switch it on and choose where spans go",
      demo: S + "7_9_maf_observability.py",
      split: [1.35, 1],
      left: [
        { type: "code", caption: "7_9_maf_observability.py (condensed)", code:
`configure_otel_providers(
    exporters=[ConsoleSpanExporter(formatter=one_line)])

with get_tracer().start_as_current_span(
        "customer_request ACC-1001"):
    result = await agent.run(
        "My balance on ACC-1001 and recent spends?")

# chat gpt-4o-mini                640 ms  tokens 240/38
# execute_tool get_balance           0 ms
# execute_tool get_recent_trans…     0 ms
# chat gpt-4o-mini                910 ms  tokens 370/96
# invoke_agent bank_assistant    1560 ms  tokens 610/134
# customer_request ACC-1001      1561 ms` },
      ],
      right: [
        { type: "table", size: 10, widths: [1.7, 2.4], head: ["Span", "Shows"], rows: [
          ["`invoke_agent`", "The whole agent run"],
          ["`chat <model>`", "Each LLM call, with token counts"],
          ["`execute_tool`", "Each tool call and its duration"],
        ] },
        { type: "text", size: 11, color: "slate", text: "Send the same spans to Jaeger, Aspire, Langfuse or Azure Monitor by changing the exporter – not the agent." },
      ],
    },
    {
      title: "AutoGen AgentChat at a Glance",
      subtitle: "Still in many codebases: in maintenance mode since October 2025 (last release 0.7.5)",
      demo: S + "7_10_autogen_bank_assistant.py",
      blocks: [
        { type: "cards", size: 10.5, items: [
          { icon: "FaMicrochip", title: "autogen-core", tag: "Foundation", lines: ["Event-driven runtime: agents exchange typed messages through handlers", "Everything else is built on top of it"] },
          { icon: "FaComments", title: "autogen-agentchat", tag: "What we code against", lines: ["AssistantAgent, teams (round-robin, selector, swarm, Magentic-One), GraphFlow", "Every AutoGen demo in this session"] },
          { icon: "FaPlug", title: "autogen-ext", tag: "Plug-ins", lines: ["Model clients (OpenAI, Anthropic, Ollama …), code executors, tools", "Swap the LLM without touching the agents"] },
        ] },
        { type: "callout", eyebrow: "Why learn it", text: "You will meet AutoGen code in existing projects – and you need to read it before you can migrate it. Each AutoGen demo below has a MAF twin." },
      ],
    },
    {
      title: "AutoGen: AssistantAgent",
      subtitle: "The same SecureBank assistant as 7_1 – compare it line by line",
      demo: S + "7_10_autogen_bank_assistant.py",
      split: [1.1, 1.1],
      left: [
        { type: "code", caption: "7_10_autogen_bank_assistant.py (condensed)", code:
`async def get_balance(account_id: str) -> str:
    """Owner and balance of an account."""
    ...

agent = AssistantAgent(
    name="bank_assistant",
    model_client=OpenAIChatCompletionClient(
        model="gpt-4o-mini"),
    system_message="You are SecureBank's ...",
    tools=[get_balance, get_forex_rate],
    reflect_on_tool_use=True,
)

await Console(agent.run_stream(
    task="ACC-1001's balance in US dollars?"))` },
      ],
      right: [
        { type: "table", size: 10, widths: [2.3, 2.1], head: ["AutoGen", "MAF (7_1)"], rows: [
          ["`AssistantAgent`", "`Agent`"],
          ["`model_client=`", "client as first argument"],
          ["`system_message=`", "`instructions=`"],
          ["plain async functions", "`@tool` functions"],
          ["`reflect_on_tool_use=True`", "default – the agent answers after tools"],
          ["`Console(run_stream())`", "`run(stream=True)`"],
        ] },
      ],
    },
    {
      title: "AutoGen: Teams and GraphFlow",
      subtitle: "A team decides who speaks next; GraphFlow fixes the order as a directed graph",
      demo: S + "7_11_autogen_round_robin_group_chat.py, 7_12_autogen_graphflow_loan_checks.py",
      blocks: [
        { type: "compare", size: 11, codeSize: 9, cols: [
          { title: "Round-robin team (7_11)", color: "navy", items: ["Writer drafts a loan-rejection letter, compliance reviews", "Stops at APPROVED or after 8 messages"], code:
`team = RoundRobinGroupChat(
    participants=[writer, compliance],
    termination_condition=
        MaxMessageTermination(8)
        | TextMentionTermination("APPROVED"))
team.run_stream(task=TASK)` },
          { title: "GraphFlow (7_12)", color: "teal", items: ["The 7_6 loan checks: credit || fraud → decision", "No checkpoints – and frozen with AutoGen"], code:
`builder = DiGraphBuilder()
for agent in [credit_officer, fraud_analyst,
              loan_decision]:
    builder.add_node(agent)
builder.add_edge(credit_officer, loan_decision)
builder.add_edge(fraud_analyst, loan_decision)
participants = builder.get_participants()
flow = GraphFlow(participants, graph=builder.build())` },
        ] },
      ],
    },
    {
      title: "Migrating: AutoGen → Agent Framework",
      subtitle: "Most concepts map one to one – the changes are names, and where state lives",
      demo: "Concept",
      blocks: [
        { type: "table", size: 10, widths: [1.9, 2.1, 2.6], head: ["AutoGen AgentChat", "Agent Framework", "What changes"], rows: [
          ["`AssistantAgent(model_client=, system_message=)`", "`Agent(client, instructions=)`", "Client is the first argument"],
          ["`tools=[func]`", "`tools=[func]`, `@tool`", "Add `approval_mode` for risky tools"],
          ["`run_stream()` + `Console`", "`run(stream=True)`", "One method, a flag for streaming"],
          ["State kept inside the agent", "`AgentSession` passed to `run()`", "Agents are stateless and reusable"],
          ["`RoundRobinGroupChat`, `SelectorGroupChat`", "`GroupChatBuilder` (+ `selection_func`)", "Turn order is a plain function"],
          ["`Swarm`, `MagenticOneGroupChat`", "`HandoffBuilder`, `MagenticBuilder`", "Same patterns, new builders"],
          ["`DiGraphBuilder` + `GraphFlow`", "`WorkflowBuilder`", "Typed messages, checkpoints, HITL"],
          ["`TextMentionTermination` …", "`termination_condition` function", "Write the rule as Python"],
        ] },
      ],
    },
    {
      title: "Migration Example: Round-Robin Team",
      subtitle: "7_11 rewritten for the Agent Framework – same agents, same task, same stop rules",
      demo: S + "7_11_autogen_round_robin_group_chat.py → 7_13_migrated_round_robin_to_maf.py",
      blocks: [
        { type: "compare", size: 11, codeSize: 9, cols: [
          { title: "AutoGen (7_11)", color: "navy", items: ["Built-in team class and termination objects"], code:
`compliance = AssistantAgent(name="compliance",
    model_client=model_client,
    system_message="... reply APPROVED if ...")

team = RoundRobinGroupChat(
    participants=[writer, compliance],
    termination_condition=
        MaxMessageTermination(8)
        | TextMentionTermination("APPROVED"))` },
          { title: "Agent Framework (7_13)", color: "teal", items: ["Turn order and stop rule are plain functions"], code:
`compliance = Agent(client, name="compliance",
    instructions="... reply APPROVED if ...")

def round_robin(state: GroupChatState) -> str:
    names = list(state.participants)
    return names[state.current_round % len(names)]

workflow = GroupChatBuilder(
    participants=[writer, compliance],
    selection_func=round_robin,
    termination_condition=compliance_approved,
    max_rounds=8).build()` },
        ] },
      ],
    },
    {
      kind: "summary",
      title: "Session 7 Summary",
      subtitle: "What you built today",
      built: [
        { tag: "7_1–7_2", title: "A SecureBank assistant", text: "Tools, sessions, complaint → ticket" },
        { tag: "7_3–7_4", title: "Guard rails", text: "Masking, audit, blocked tools, human approval" },
        { tag: "7_5–7_8", title: "Workflows", text: "Routing, resumable loan checks, orchestrations, handoff desk" },
        { tag: "7_9", title: "Tracing", text: "OpenTelemetry spans for every step" },
        { tag: "7_10–7_13", title: "AutoGen → MAF", text: "AgentChat twins and a migrated team" },
      ],
      takeaways: [
        "MAF is the successor to AutoGen and Semantic Kernel",
        "Agents for open-ended steps, workflows when you own the order",
        "Middleware and approvals keep policy out of prompts",
        "Checkpoints make long workflows resumable",
        "AutoGen → MAF is mostly renaming; team rules become plain functions",
      ],
      next: "Session 8: Agentic RAG and GraphRAG for Agents",
    },
  ],
};
