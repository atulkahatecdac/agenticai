const M = "17_Monitoring_Evaluation_and_Fine_Tuning/";

module.exports = {
  section: "Module 17 – Monitoring, Evaluation and Fine-Tuning",
  slides: [
    {
      kind: "opener",
      eyebrow: "Module 17",
      title: "Monitoring, Evaluation and Fine-Tuning",
      subtitle: "Watch an agent in detail and over time – and, when prompting isn't enough, change the model itself",
      goals: [
        { icon: "FaMagnifyingGlassChart", title: "Trace one run in detail", text: "OpenTelemetry spans and attributes; Jaeger waterfalls" },
        { icon: "FaChartLine", title: "Watch behaviour over time", text: "Prometheus metrics and Grafana dashboards" },
        { icon: "FaBullseye", title: "Set reliability targets", text: "SLA, SLO and SLI; LLM-specific observability" },
        { icon: "FaSliders", title: "Fine-tune efficiently", text: "when to fine-tune; LoRA, QLoRA, PEFT, RLHF and DPO" },
      ],
      agenda: [
        "OpenTelemetry for a LangGraph agent",
        "Jaeger and the trace waterfall",
        "Prometheus, Grafana, PromQL and alerts",
        "SLA, SLO and SLI",
        "Embedding drift; Arize Phoenix tracing",
        "Cost per run and budgets per user",
        "Prompting vs fine-tuning; data from traces",
        "LoRA, QLoRA and PEFT",
        "RLHF and DPO",
      ],
    },
    {
      title: "OpenTelemetry for AI Agents",
      subtitle: "The open standard for telemetry – ideal for seeing inside complex agent workflows",
      demo: M + "17_1_opentelemetry_langgraph.py",
      split: [1, 1.2],
      left: [
        { type: "icons", d: 0.38, size: 11, items: [
          { icon: "FaRoute", title: "Trace", text: "One complete execution of the agent" },
          { icon: "FaRulerHorizontal", title: "Span", text: "One operation inside it – a node, an LLM call, a lookup" },
          { icon: "FaTag", title: "Attribute", text: "A key-value fact on a span: model, tokens, intent, cache hit" },
        ] },
        { type: "callout", eyebrow: "No spans at all?", text: "Check the OS environment for `OTEL_SDK_DISABLED=true` – other tools often set it machine-wide." },
      ],
      right: [
        { type: "code", caption: "Instrumenting a LangGraph node (condensed)", code:
`provider = TracerProvider()
provider.add_span_processor(
    SimpleSpanProcessor(ConsoleSpanExporter()))
tracer = provider.get_tracer("my-langgraph-agent")

def classify_intent(state):
    with tracer.start_as_current_span("classify_intent") as span:
        result = llm.invoke(...)
        span.set_attribute("gen_ai.request.model", "gpt-4o-mini")
        span.set_attribute("securelife.intent", result.intent)
        return {"intent": result.intent}

with tracer.start_as_current_span("support_turn"):   # root
    app.invoke(initial_state)` },
      ],
    },
    {
      title: "Jaeger: The Trace Waterfall",
      subtitle: "Export the same spans over OTLP and see the whole LangGraph run as a timeline",
      demo: M + "17_2_jaeger_trace_waterfall.py",
      split: [1, 1.1],
      left: [
        { type: "flow", items: [
          { icon: "FaDiagramProject", label: "Agent", caption: "Creates spans" },
          { icon: "FaPaperPlane", label: "OTLP exporter", caption: "HTTP on port 4318", color: "coral" },
          { icon: "FaChartGantt", label: "Jaeger", caption: "Waterfall UI on 16686", color: "teal" },
        ] },
        { type: "text", size: 11, color: "slate", text: "The waterfall shows what ran, in what order, for how long – and what overlapped – without reading timestamps by hand." },
      ],
      right: [
        { type: "code", caption: "1 – start Jaeger", code:
`docker run -d --name jaeger --rm ^
  -p 16686:16686 -p 4317:4317 -p 4318:4318 ^
  jaegertracing/all-in-one:latest` },
        { type: "steps", size: 10.5, gap: 0.08, items: [
          { title: "Run the script" },
          { title: "Open localhost:16686" },
          { title: "Service: securelife-insurance-agent → Find traces" },
        ] },
      ],
    },
    {
      title: "Prometheus and Grafana",
      subtitle: "A trace is a microscope on one turn; metrics are a dashboard of behaviour over time",
      demo: M + "17_3_prometheus_metrics_agent.py + monitoring/",
      split: [1, 1.1],
      left: [
        { type: "flow", items: [
          { icon: "FaRobot", label: "Agent", caption: "Serves :8000/metrics" },
          { icon: "FaDatabase", label: "Prometheus", caption: "Scrapes it; UI on 9095", color: "coral" },
          { icon: "FaChartLine", label: "Grafana", caption: "Dashboards on 3000", color: "teal" },
        ] },
        { type: "text", size: 11, color: "slate", text: "Prometheus pulls metrics at regular intervals; Grafana charts latency, token cost and error rate." },
      ],
      right: [
        { type: "code", caption: "Metrics the agent exposes", code:
`REQUESTS_TOTAL        = Counter(...)
NODE_DURATION_SECONDS = Histogram(...)
NODE_ERRORS_TOTAL     = Counter(...)
LLM_TOKENS_TOTAL      = Counter(...)
TURN_DURATION_SECONDS = Histogram(...)

start_http_server(8000)   # /metrics` },
        { type: "text", size: 10.5, color: "slate", text: "Prometheus listens on 9095 here, not 9090, to avoid a clash with the Langfuse demo's MinIO." },
      ],
    },
    {
      title: "PromQL and Alerting",
      subtitle: "Every Grafana panel is a PromQL query; an alert is a query that returns rows only when something is wrong",
      demo: M + "monitoring/prometheus/alert_rules.yml  →  :9095/alerts",
      split: [1.1, 1],
      left: [
        { type: "table", size: 9.5, widths: [2.6, 1.3], head: ["PromQL", "Reads as"], rows: [
          ["sum(rate(securelife_agent_requests_total[1m])) * 60", "Turns per minute"],
          ["histogram_quantile(0.95, sum by (le) (rate(..._turn_duration_seconds_bucket[5m])))", "p95 turn latency"],
          ["sum by (node) (increase(..._node_errors_total[5m]))", "Errors per node, last 5 min"],
          ["sum by (token_type) (rate(..._llm_tokens_total[1m]))", "Token burn rate"],
        ] },
        { type: "text", size: 10, color: "slate", text: "`rate()` turns an ever-growing counter into a per-second speed; `histogram_quantile()` turns buckets into a percentile." },
      ],
      right: [
        { type: "code", caption: "alert_rules.yml (one of four rules)", code:
`- alert: AgentTurnLatencyHigh
  expr: |
    histogram_quantile(0.95, sum by (le) (rate(
      securelife_agent_turn_duration_seconds_bucket[5m]
    ))) > 8
  for: 2m          # must stay bad for 2 minutes
  labels: { severity: warning }
  annotations:
    summary: "p95 is {{ $value }}s (SLO 8s)"` },
        { type: "bullets", size: 10.5, items: [
          "Also: error rate > 5%, token burn above budget, agent down (`up == 0`)",
          "Checked with `promtool check rules` – 4 rules",
          "Production: Prometheus → Alertmanager → Slack / PagerDuty",
        ] },
      ],
    },
    {
      title: "LLM-Specific Observability and Reliability Targets",
      subtitle: "\"Did the API return 200?\" isn't enough – \"Was the answer actually good?\" is the question",
      demo: "Concept",
      split: [1, 1.15],
      left: [
        { type: "icons", d: 0.38, size: 11, items: [
          { icon: "FaChartColumn", title: "Arize AI", text: "Observability platform for ML and LLM apps (paid, limited free tier)" },
          { icon: "FaFire", title: "Phoenix", text: "Arize's open-source tool – tracing and evaluation for LLM, RAG and agent apps" },
        ] },
      ],
      right: [
        { type: "table", size: 10, widths: [1.5, 1.9, 1.8], head: ["Term", "Meaning", "Example"], rows: [
          ["SLA – agreement", "Promise to the customer", "≥ 99.9% available"],
          ["SLO – objective", "Stricter internal target", "≥ 99.95% successful"],
          ["SLI – indicator", "What is actually measured", "99.92% this month"],
        ] },
        { type: "callout", eyebrow: "Read the example", text: "The SLI missed the SLO but not the SLA – an early warning to tighten reliability before a customer promise is broken." },
      ],
    },
    {
      title: "Embedding Drift: Users Ask New Things",
      subtitle: "Nothing errors and latency is fine – only the meaning of the traffic has moved. Three checks catch it",
      demo: M + "17_5_embedding_drift.py   (no LLM, no API key)",
      split: [1, 1.05],
      left: [
        { type: "image", src: "embedding_drift.png", alt: "This week's queries form a new cluster with no knowledge-base points near it" },
        { type: "text", size: 10, color: "slate", text: "A new EV wall charger launched; the help-desk KB has nothing on it." },
      ],
      right: [
        { type: "table", size: 9.5, widths: [1.45, 2.3], head: ["Check", "Result this week"], rows: [
          ["1. Centroid distance", "0.284 vs 0.248 chance level (bootstrap) → DRIFT"],
          ["2. KB coverage", "Queries with no good KB match: 9% → 45%"],
          ["3. New clusters", "8 queries, best KB match 0.26 – all about the EV charger"],
        ] },
        { type: "text", size: 10.5, text: "**Why three:** only 8 of 22 queries changed, so the average moves just past the noise. Checks 2 and 3 look at each query and name the new topic." },
        { type: "text", size: 10, color: "slate", text: "**Not covered: Phoenix's \"Inferences\" drift view** – current Phoenix (v21) removed it. The maths above is what it computed." },
      ],
    },
    {
      title: "Arize Phoenix: Tracing in One Line",
      subtitle: "OpenInference instrumentors already know what an LLM call, a prompt and a retriever are",
      demo: M + "17_6_phoenix_tracing.py  (own venv: 17_6_requirements.txt)",
      split: [1.1, 1],
      left: [
        { type: "code", caption: "Terminal 1", code: `phoenix serve          # UI + collector on :6006` },
        { type: "code", caption: "Terminal 2 – 17_6_phoenix_tracing.py (condensed)", code:
`from phoenix.otel import register

register(endpoint="http://localhost:6006/v1/traces",
         project_name="helpdesk-rag",
         auto_instrument=True)     # finds LangChain itself

chain = ({"context": faq_retriever, "question": ...}
         | prompt | ChatOpenAI(model="gpt-4o-mini"))
chain.invoke("Can I pay with UPI?")   # traced` },
      ],
      right: [
        { type: "table", size: 10, widths: [1.3, 2.4], head: ["17_1 / 17_2", "17_6 Phoenix"], rows: [
          ["You create spans and set attributes", "Spans and LLM attributes come for free"],
          ["Generic: Jaeger shows timings", "LLM-aware: prompt text, tokens, retrieved docs"],
          ["Any app", "LLM apps; plus evals on the traces"],
        ] },
        { type: "text", size: 10.5, color: "slate", text: "Tested: three questions → three traces in project helpdesk-rag. Phoenix needs its own venv because it pins newer OpenTelemetry packages than this repo." },
      ],
    },
    {
      title: "Cost per Run, Budgets per User",
      subtitle: "Every response carries its token usage – one callback can price it, cap it and raise an alert",
      demo: M + "17_7_cost_tracking_token_budget.py",
      split: [1.15, 1],
      left: [
        { type: "code", caption: "17_7 (condensed)", code:
`class CostTracker(BaseCallbackHandler):
    def on_chat_model_start(self, s, m, *, run_id,
                            metadata, **kw):
        self.who[run_id] = metadata     # who is calling

    def on_llm_end(self, response, *, run_id, **kw):
        msg = response.generations[0][0].message
        u = msg.usage_metadata
        cost = (u["input_tokens"] * 0.15
                + u["output_tokens"] * 0.60) / 1e6
        self.spent[user] += cost        # + alert at 80%

def ask(user, plan, question):
    tracker.check(user, plan)           # BEFORE the call
    meta = {"user": user, "plan": plan}
    return llm.invoke(question, config={"metadata": meta})` },
      ],
      right: [
        { type: "steps", size: 10.5, items: [
          { title: "Price every call", text: "Tokens × the model's price, per user and per model" },
          { title: "Alert early", text: "80% of a daily budget → a warning (Slack, PagerDuty)" },
          { title: "Refuse at 100%", text: "Check before calling, so the over-budget call never happens" },
        ] },
        { type: "callout", eyebrow: "In the demo", text: "The free-plan user passes 80% on their first call and is refused on the next two; the pro user is unaffected." },
      ],
    },

    // ---------------------------------------------------------------- fine-tuning
    {
      title: "Prompting or Fine-Tuning?",
      subtitle: "Prompting guides an existing model; fine-tuning trains it further on a prepared dataset",
      demo: "Concept",
      blocks: [
        { type: "compare", size: 11, cols: [
          { title: "Prompting / RAG", color: "navy", items: ["Instructions, context, examples, constraints", "Information that changes – e.g. company policy → RAG or tools", "Cheap to change, instant to deploy"] },
          { title: "Fine-tuning", color: "teal", items: ["A behaviour, style or task done consistently", "e.g. classify complaints in your own labelling scheme", "Needs data, compute and evaluation"] },
        ] },
        { type: "callout", eyebrow: "Rule of thumb", text: "Don't fine-tune just because the model doesn't know your latest information – retrieve it instead." },
      ],
    },
    {
      title: "From Traces to a Training Set",
      subtitle: "Your traced runs are real questions and real answers – the well-rated ones are fine-tuning data",
      demo: M + "17_8_finetuning_dataset_from_traces.py",
      split: [1, 1.1],
      left: [
        { type: "steps", size: 10.5, gap: 0.08, items: [
          { title: "Keep", text: "Thumbs-up feedback and no error (LangSmith feedback_stats)" },
          { title: "Scrub", text: "Phones, e-mails, card numbers → <PHONE>, <EMAIL>, <CARD>" },
          { title: "Dedupe", text: "The same Q&A twice teaches nothing" },
          { title: "Split", text: "80/20 – the test set is never trained on" },
          { title: "Write", text: "Chat JSONL – OpenAI fine-tuning, Hugging Face TRL, Unsloth" },
        ] },
      ],
      right: [
        { type: "code", caption: "One line of data/finetune_train.jsonl", code:
`{"messages": [
  {"role": "system", "content": "You are the support
      assistant for an online store..."},
  {"role": "user", "content": "My refund hasn't come.
      Call me on <PHONE> or mail <EMAIL>"},
  {"role": "assistant", "content": "I'm sorry about
      the delay, Priya. Refunds reach your account..."}]}` },
        { type: "text", size: 10.5, color: "slate", text: "Sample run: 16 traces → 12 kept (1 error, 2 not liked, 1 duplicate dropped), PII masked in 2 fields → 9 train, 3 test. Real projects start at a few hundred good examples." },
      ],
    },
    {
      title: "LoRA: Low-Rank Adaptation",
      subtitle: "Freeze the original weights and learn a small update beside them",
      demo: M + "17_4_lora_sentiment_finetuning.py",
      split: [1, 1.1],
      left: [
        { type: "compare", size: 10.5, cols: [
          { title: "Full fine-tuning", color: "slate", items: ["W → W + ΔW", "ΔW is as big as W – enormous"] },
          { title: "LoRA", color: "teal", items: ["ΔW ≈ B·A, two thin matrices", "W′ = W + B·A; W untouched", "Merge B·A in for no extra latency"] },
        ] },
        { type: "callout", eyebrow: "The arithmetic", text: "A 4096 × 4096 layer has 16.8M weights. With rank r = 8, A and B hold 8×4096 + 4096×8 = 65,536 – about 0.4%." },
      ],
      right: [
        { type: "code", caption: "17_4 – LoRA on DistilBERT for sentiment", code:
`lora_config = LoraConfig(
    task_type=TaskType.SEQ_CLS,
    r=8,
    lora_alpha=16,
    lora_dropout=0.1,
    target_modules=["q_lin", "v_lin"],
    modules_to_save=["pre_classifier", "classifier"])

lora_model = get_peft_model(base_model, lora_config)
lora_model.print_trainable_parameters()` },
        { type: "text", size: 10.5, color: "slate", text: "PEFT – parameter-efficient fine-tuning – is both the family of techniques and the Hugging Face library that implements LoRA, QLoRA and more." },
      ],
    },
    {
      title: "QLoRA: Quantisation + LoRA",
      subtitle: "Store the frozen base model in fewer bits, and train only the small adapters",
      demo: "Concept",
      split: [1, 1.1],
      left: [
        { type: "table", size: 10.5, widths: [1.6, 2.2], head: ["7B model stored as", "Approx. GPU memory"], rows: [
          ["FP32", "28 GB"],
          ["FP16", "14 GB"],
          ["INT8", "7 GB"],
          ["4-bit", "3.5 GB"],
        ] },
      ],
      right: [
        { type: "icons", d: 0.4, items: [
          { icon: "FaCompress", title: "Quantisation", text: "Stores the pretrained weights with fewer bits" },
          { icon: "FaSliders", title: "LoRA", text: "Cuts the number of trainable parameters" },
          { icon: "FaMicrochip", title: "Together", text: "Fine-tune large models on a single consumer GPU" },
        ] },
      ],
    },
    { kind: "image", src: "rlhf_vs_dpo.png", alt: "RLHF trains a reward model then uses RL; DPO trains directly on preference pairs", demo: "Concept" },
    {
      kind: "summary",
      title: "Module 17 Summary",
      subtitle: "What you built",
      built: [
        { tag: "17_1", title: "Traces", text: "OpenTelemetry spans, a Jaeger waterfall, Phoenix" },
        { tag: "17_3", title: "Metrics and alerts", text: "Prometheus, Grafana, four alert rules" },
        { tag: "17_5", title: "Drift checks", text: "A new topic found by its embeddings" },
        { tag: "17_7", title: "A cost guard", text: "Per-user budgets, alerts and refusals" },
        { tag: "17_8", title: "Training data", text: "Clean JSONL from rated production traces" },
        { tag: "17_4", title: "A LoRA adapter", text: "Sentiment fine-tuning with PEFT" },
      ],
      takeaways: [
        "Traces explain one run; metrics show trends",
        "Monitor answer quality, not just uptime",
        "Set SLOs tighter than your SLAs",
        "Retrieve changing facts; fine-tune stable behaviour",
        "LoRA and QLoRA make fine-tuning affordable",
      ],
      next: "Module 18: Dockerizing and Deploying AI Agents",
    },
  ],
};
