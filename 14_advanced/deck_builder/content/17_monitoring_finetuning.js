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
        "Prometheus and Grafana",
        "Arize Phoenix",
        "SLA, SLO and SLI",
        "Prompting vs fine-tuning",
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
        { tag: "17_1", title: "OpenTelemetry spans", text: "A LangGraph agent instrumented node by node" },
        { tag: "17_2", title: "Jaeger waterfall", text: "The same spans as a timeline" },
        { tag: "17_3", title: "Prometheus metrics", text: "Counters and histograms in Grafana" },
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
