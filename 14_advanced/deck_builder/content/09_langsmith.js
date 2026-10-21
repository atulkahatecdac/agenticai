const M = "09_langsmith/";

module.exports = {
  section: "Module 09 – LangSmith",
  slides: [
    {
      kind: "opener",
      eyebrow: "Module 09",
      title: "LangSmith: Tracing, Testing and Evaluation",
      subtitle: "See inside every run, build test datasets, and measure whether a change made things better or worse",
      goals: [
        { icon: "FaEye", title: "Trace an agent end to end", text: "every prompt, tool call, token and latency" },
        { icon: "FaDatabase", title: "Create evaluation datasets", text: "golden Q&A pairs and edge cases" },
        { icon: "FaGavel", title: "Score answers automatically", text: "LLM-as-a-judge and heuristic evaluators" },
        { icon: "FaChartLine", title: "Compare and monitor", text: "prompt regression, A/B tests, dashboards" },
      ],
      agenda: [
        "LangSmith and instrumentation",
        "Evaluation datasets",
        "LLM-as-a-judge",
        "Heuristic evaluators",
        "Prompt regression testing",
        "A/B testing agent behaviours",
        "Human feedback on runs",
        "Production monitoring dashboards",
      ],
    },
    {
      title: "LangSmith",
      subtitle: "LangChain's platform for monitoring, debugging, testing and evaluating LLM applications",
      demo: M + "trace_langgraph_agent_end_to_end.py",
      split: [1.1, 1],
      left: [
        { type: "flow", items: [
          { icon: "FaUser", label: "User", caption: "Asks a question" },
          { icon: "FaDiagramProject", label: "Your app", caption: "LangChain / LangGraph" },
          { icon: "FaCloudArrowUp", label: "LangSmith SDK", caption: "Sends each run", color: "coral" },
          { icon: "FaChartColumn", label: "Dashboard", caption: "Traces, metrics, evaluations", color: "teal" },
        ] },
        { type: "steps", size: 10.5, gap: 0.08, items: [
          { title: "Create an account and an API key", text: "smith.langchain.com" },
          { title: "Set the environment variables" },
          { title: "Run the app – tracing is automatic", text: "LangChain and LangGraph report every step" },
        ] },
      ],
      right: [
        { type: "code", caption: ".env", code:
`LANGSMITH_TRACING="true"
LANGSMITH_ENDPOINT="https://api.smith.langchain.com"
LANGSMITH_API_KEY="your api key"
LANGSMITH_PROJECT="my-project"` },
        { type: "callout", eyebrow: "In a trace", text: "The run tree: each node, prompt, tool call and LLM call, with inputs, outputs, tokens and timing." },
      ],
    },
    {
      title: "Evaluation Datasets",
      subtitle: "A fixed set of test cases you run every version of the app against",
      demo: M + "creating_evaluation_datasets.py",
      split: [1, 1.15],
      left: [
        { type: "icons", d: 0.38, size: 11, items: [
          { icon: "FaFileLines", title: "Each example holds", text: "An input question, the expected answer, optional context, evaluation criteria" },
          { icon: "FaMedal", title: "Golden Q&A pairs", text: "Trusted reference answers known to be correct" },
          { icon: "FaTriangleExclamation", title: "Edge cases", text: "Ambiguous, very long, misspelt or incomplete questions", color: "coral" },
        ] },
      ],
      right: [
        { type: "code", caption: "creating_evaluation_datasets.py (condensed)", code:
`client.create_dataset(DATASET_NAME)
client.create_examples(dataset_name=DATASET_NAME,
                       examples=EXAMPLES)

def predict(inputs):
    prompt = ("Answer briefly. If the question is too "
              "ambiguous to answer, say so plainly.\\n\\n"
              f"Question: {inputs['question']}")
    return {"answer": llm.invoke(prompt).content}

evaluate(predict, data=DATASET_NAME,
         evaluators=[llm_judge])` },
      ],
    },
    {
      title: "LLM-as-a-Judge",
      subtitle: "Use a second LLM to grade answers at scale – the approach behind LangSmith, RAGAS, DeepEval and OpenAI Evals",
      demo: M + "langsmith_llm_as_judge.py",
      split: [1, 1.2],
      left: [
        { type: "chain", size: 10, items: ["Question", "App LLM", "Answer", "Judge LLM", "Score + feedback"], highlight: [3] },
        { type: "text", text: "**Send the judge:** the question, the expected answer, any retrieved context, the generated answer, and clear grading instructions.", size: 11 },
        { type: "callout", eyebrow: "Tip", text: "Ask for structured output – a verdict plus a one-line reason – so scores are machine-readable." },
      ],
      right: [
        { type: "code", caption: "langsmith_llm_as_judge.py (condensed)", code:
`def llm_judge(run, example):
    prompt = f"""Review a support bot's answer
against company policy. Wording may differ;
a wrong number or missing condition is wrong.
Question: {example.inputs['question']}
Reference: {example.outputs['answer']}
Bot's answer: {run.outputs['answer']}"""
    v = judge_llm.with_structured_output(
            Verdict).invoke(prompt)
    return {"results": [
      {"key": "policy_correctness",
       "score": int(v.correct)},
      {"key": "quality_score", "score": v.score}]}` },
      ],
    },
    {
      title: "Heuristic Evaluators",
      subtitle: "Rule-based checks: fast, deterministic, free – but blind to meaning",
      demo: "Concept",
      blocks: [
        { type: "compare", size: 11, cols: [
          { title: "Heuristic (rules)", color: "navy", items: ["Is the output under 200 words?", "Is it valid JSON?", "Does it mention \"refund\" and \"14 days\"?", "Does the email address pass validation?"] },
          { title: "LLM-as-a-judge", color: "teal", items: ["Is the answer correct?", "Is it relevant to the question?", "Is it grounded in the context?", "Is the tone right?"] },
        ] },
        { type: "callout", eyebrow: "Use both", text: "Run cheap heuristic checks on everything; spend judge calls on the questions only an LLM can answer." },
      ],
    },
    {
      title: "Prompt Regression Testing",
      subtitle: "Did the new prompt do better, worse or the same as the old one – on the same dataset?",
      demo: M + "prompt_regression_testing.py",
      split: [1, 1.1],
      left: [
        { type: "bullets", size: 11.5, items: [
          "Did accuracy improve?",
          "Did hallucinations increase?",
          "Did response quality drop?",
          "Did previously correct answers become wrong?",
        ] },
        { type: "callout", eyebrow: "Treat prompts like code", text: "Every prompt change gets the same test suite before it ships." },
      ],
      right: [
        { type: "flow", items: [
          { icon: "FaDatabase", label: "Same dataset", caption: "Fixed questions + references" },
          { icon: "FaCodeCompare", label: "Prompt v1 vs v2", caption: "One experiment each" },
          { icon: "FaGavel", label: "Same judge", caption: "Identical scoring", color: "coral" },
          { icon: "FaChartColumn", label: "Compare", caption: "Side by side in LangSmith", color: "teal" },
        ] },
      ],
    },
    {
      title: "A/B Testing Agent Behaviours",
      subtitle: "Compare two whole versions of an agent under the same conditions – not just two prompts",
      demo: M + "ab_testing.py",
      split: [1, 1.1],
      left: [
        { type: "text", text: "**What you might compare**", size: 12 },
        { type: "bullets", size: 11, items: [
          "Direct answer vs tool-assisted answer",
          "Single-step vs multi-step reasoning",
          "One tool vs several tools",
          "A small model vs a large model",
          "Short vs detailed responses",
        ] },
      ],
      right: [
        { type: "code", caption: "ab_testing.py – two experiments, one dataset", code:
`results_a = evaluate(predict_a, data=DATASET_NAME,
    experiment_prefix="ab-variant-a-concise")
results_b = evaluate(predict_b, data=DATASET_NAME,
    experiment_prefix="ab-variant-b-detailed")` },
        { type: "text", size: 11, color: "slate", text: "LangSmith lines the two experiments up example by example, so you see where each variant wins." },
      ],
    },
    {
      title: "Annotating Runs with Human Feedback",
      subtitle: "People review real responses; their judgements become evaluation and training data",
      demo: "Concept",
      split: [1, 1.1],
      left: [
        { type: "text", text: "**Reviewers may give**", size: 12 },
        { type: "tiles", cols: 2, size: 10, titleSize: 11, items: [
          { icon: "FaStar", title: "A rating (1–5)" },
          { icon: "FaThumbsUp", title: "Thumbs up / down" },
          { icon: "FaCheck", title: "Correct / incorrect" },
          { icon: "FaPen", title: "A better answer" },
          { icon: "FaCodeCompare", title: "A preference: A or B" },
          { icon: "FaComment", title: "Comments on mistakes" },
        ] },
      ],
      right: [
        { type: "callout", eyebrow: "Where it leads", text: "Collected preferences are what RLHF and DPO train on (Module 17) – humans teach the model what \"better\" means." },
        { type: "text", size: 11, color: "slate", text: "In LangSmith, feedback attaches to a run, so you can filter for bad answers and add them to your dataset." },
      ],
    },
    {
      title: "Production Monitoring Dashboards",
      subtitle: "Catch slow responses, rising failures, unexpected cost and quality drift before users do",
      demo: "Concept",
      split: [1.1, 1],
      left: [
        { type: "table", size: 10, widths: [1.3, 2.1, 1.3], head: ["Metric", "What it tells us", "Example"], rows: [
          ["Latency", "How fast it responds", "2.4 s / request"],
          ["Error rate", "How often requests fail", "1.8%"],
          ["Volume", "How much it is used", "50K requests / day"],
          ["Tokens", "How much LLM work", "120M tokens"],
          ["Cost", "Operating spend", "$450 / day"],
          ["Throughput", "Requests per second", "30 req / s"],
        ] },
      ],
      right: [
        { type: "text", text: "**AI-specific signals**", size: 12 },
        { type: "bullets", size: 10.5, items: [
          "Model choice and prompt/token usage",
          "Hallucination and quality scores",
          "Retrieval quality and RAG faithfulness",
          "Tool-call success rate; agent paths",
          "Guardrail violations; user feedback",
        ] },
      ],
    },
    {
      kind: "summary",
      title: "Module 09 Summary",
      subtitle: "What you built",
      built: [
        { tag: "trace", title: "End-to-end traces", text: "A LangGraph agent, fully visible in LangSmith" },
        { tag: "data", title: "An evaluation dataset", text: "Golden answers plus edge cases" },
        { tag: "judge", title: "LLM-as-a-judge", text: "Structured verdicts on policy correctness" },
        { tag: "A/B", title: "Experiments", text: "Prompt regression and agent A/B tests" },
      ],
      takeaways: [
        "You can't improve what you can't see – trace everything",
        "A fixed dataset makes changes comparable",
        "Judge with an LLM; check with rules",
        "Test every prompt change like a code change",
        "Monitor quality, not just uptime",
      ],
      next: "Module 10: Model Context Protocol (MCP)",
    },
  ],
};
