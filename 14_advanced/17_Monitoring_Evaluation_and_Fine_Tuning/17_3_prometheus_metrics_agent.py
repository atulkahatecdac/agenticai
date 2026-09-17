import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")

import itertools
import sys
import time
from contextlib import contextmanager
from typing import Literal, TypedDict
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from prometheus_client import Counter, Histogram, start_http_server

load_dotenv(override=True)
sys.stdout.reconfigure(encoding="utf-8")

# =====================================================================
# 17_1/17_2 answered "what happened during ONE turn, in detail" - a trace is a
# microscope. Prometheus + Grafana answer a different question: "how is the
# agent behaving OVER TIME, across many turns" - a dashboard, not a microscope.
# Same instrumented LangGraph agent as 17_1/17_2; different telemetry shape.
#
# TRACES vs METRICS, the actual distinction:
#   - A trace/span carries unlimited detail (any string attribute, any
#     cardinality) but is thrown away/aggregated after inspection - nobody
#     graphs "average trace" over a week of individual spans.
#   - A metric is a small set of numbers (counters, histograms) with LOW-
#     CARDINALITY labels, cheap to store forever and to alert on ("p95 latency
#     > 2s for 5 minutes") - but it can't tell you what one specific slow
#     request looked like. That's why real systems run both, not one or the
#     other.
#
# PULL vs PUSH - the other big difference from 17_2's OTLP exporter:
#   - The Jaeger script PUSHED: it opened a connection and sent each batch of
#     spans TO Jaeger.
#   - Prometheus PULLS: this script just exposes an HTTP endpoint
#     (localhost:8000/metrics, plain text) and Prometheus itself scrapes that
#     endpoint on a timer (5s here - prometheus.yml). That means this script
#     has to stay RUNNING to be scraped more than once - a one-shot script
#     exiting immediately would give Prometheus nothing to plot a trend from,
#     which is why __main__ below loops for a while instead of running once.
#
# SETUP - two containers, run together from the monitoring/ folder next to
# this script:
#
#   cd 14_advanced/17_Monitoring_Evaluation_and_Fine_Tuning/monitoring
#   docker compose up -d
#
# That starts:
#   - Prometheus  (localhost:9095) - scrapes THIS script's :8000/metrics
#     endpoint every 5s (see monitoring/prometheus/prometheus.yml).
#   - Grafana     (localhost:3000, admin/admin, anonymous viewer access on) -
#     pre-provisioned with the Prometheus datasource AND a ready-made
#     "SecureLife Insurance Agent - Metrics" dashboard (see
#     monitoring/grafana/), so there's nothing to click together manually.
#
#   pip install prometheus-client
#
# Then just run this script - it starts its own :8000/metrics server, runs a
# batch of support turns with a short pause between each (so Prometheus's
# 5s scrapes catch multiple distinct points), then lingers for a bit so the
# dashboard still has a live target to look at before the process exits.
# =====================================================================

METRICS_PORT = 8000

REQUESTS_TOTAL = Counter(
    "securelife_agent_requests_total",
    "Completed SecureLife support turns, labeled by the intent classify_intent resolved.",
    ["intent"],
)
NODE_DURATION_SECONDS = Histogram(
    "securelife_agent_node_duration_seconds",
    "Wall-clock duration of each LangGraph node.",
    ["node"],
)
NODE_ERRORS_TOTAL = Counter(
    "securelife_agent_node_errors_total",
    "Node executions that raised an exception, labeled by node.",
    ["node"],
)
LLM_TOKENS_TOTAL = Counter(
    "securelife_agent_llm_tokens_total",
    "Cumulative LLM token usage, labeled by node and direction (input/output).",
    ["node", "token_type"],
)
TURN_DURATION_SECONDS = Histogram(
    "securelife_agent_turn_duration_seconds",
    "Wall-clock duration of one full support turn, start to final response.",
)


@contextmanager
def track_node(node_name: str):
    # The metrics equivalent of 17_1/17_2's `with tracer.start_as_current_span(...)`
    # - same "time it, tag errors, always record" shape, just writing to a
    # Counter/Histogram pair instead of building a span.
    start = time.perf_counter()
    try:
        yield
    except Exception:
        NODE_ERRORS_TOTAL.labels(node=node_name).inc()
        raise
    finally:
        NODE_DURATION_SECONDS.labels(node=node_name).observe(time.perf_counter() - start)


llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

SECURELIFE_KB = {
    "claim_status": "Claims are typically reviewed within 5-7 business days of submission.",
    "coverage_question": "Pre-existing conditions are covered after a waiting period of 2 to 4 years from the policy start date.",
}


class IntentResult(BaseModel):
    intent: Literal["claim_status", "coverage_question", "general"] = Field(
        description="The single best-matching category for the customer's message."
    )


intent_llm = llm.with_structured_output(IntentResult, include_raw=True)


class SupportState(TypedDict):
    query: str
    intent: str
    context: str
    response: str


def classify_intent(state: SupportState) -> SupportState:
    with track_node("classify_intent"):
        result = intent_llm.invoke(
            "Classify this SecureLife customer message into exactly one category - "
            f"claim_status, coverage_question, or general: {state['query']!r}"
        )
        parsed: IntentResult = result["parsed"]
        usage = getattr(result["raw"], "usage_metadata", None) or {}

        LLM_TOKENS_TOTAL.labels(node="classify_intent", token_type="input").inc(usage.get("input_tokens", 0))
        LLM_TOKENS_TOTAL.labels(node="classify_intent", token_type="output").inc(usage.get("output_tokens", 0))

        return {"intent": parsed.intent}


def retrieve_policy_context(state: SupportState) -> SupportState:
    with track_node("retrieve_policy_context"):
        article = SECURELIFE_KB.get(state["intent"])
        return {"context": article or "No specific KB article - answer from general policy knowledge."}


def generate_response(state: SupportState) -> SupportState:
    with track_node("generate_response"):
        messages = [
            SystemMessage(
                content=(
                    "You are Meera, SecureLife Insurance's customer support agent. "
                    f"Relevant reference material: {state['context']}"
                )
            ),
            HumanMessage(content=state["query"]),
        ]
        ai_message = llm.invoke(messages)

        usage = ai_message.usage_metadata or {}
        LLM_TOKENS_TOTAL.labels(node="generate_response", token_type="input").inc(usage.get("input_tokens", 0))
        LLM_TOKENS_TOTAL.labels(node="generate_response", token_type="output").inc(usage.get("output_tokens", 0))

        return {"response": ai_message.content}


graph = StateGraph(SupportState)
graph.add_node("classify_intent", classify_intent)
graph.add_node("retrieve_policy_context", retrieve_policy_context)
graph.add_node("generate_response", generate_response)
graph.add_edge(START, "classify_intent")
graph.add_edge("classify_intent", "retrieve_policy_context")
graph.add_edge("retrieve_policy_context", "generate_response")
graph.add_edge("generate_response", END)

app = graph.compile()


def run_support_turn(query: str) -> str:
    start = time.perf_counter()
    result = app.invoke({"query": query, "intent": "", "context": "", "response": ""})
    TURN_DURATION_SECONDS.observe(time.perf_counter() - start)
    REQUESTS_TOTAL.labels(intent=result["intent"]).inc()
    return result["response"]


def banner(title: str) -> None:
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


# Cycled repeatedly so a short demo run still produces enough samples (and a
# realistic mix of intents) for the dashboard's rate()/histogram_quantile()
# queries to have something to compute over.
DEMO_QUERIES = [
    "How long does it take for a claim to be reviewed?",
    "Is my pre-existing diabetes covered after 3 years on the policy?",
    "What are your office hours?",
    "Can you check the status of my claim from last week?",
    "Does the policy cover a pre-existing heart condition?",
]

NUM_TURNS = 24  # ~2 minutes of turns at SLEEP_BETWEEN_TURNS below - several 5s Prometheus scrapes
SLEEP_BETWEEN_TURNS_SECONDS = 5
LINGER_SECONDS = 90  # keep /metrics serving after the last turn so Grafana still has a live target to show

HOW_TO_READ_THE_DASHBOARD = """
  1. Open Grafana at http://localhost:3000 (log in as admin/admin, or skip
     login entirely - anonymous viewer access is enabled for this demo).
  2. Dashboards -> "SecureLife Insurance Agent - Metrics" is already there
     (pre-provisioned from monitoring/grafana/dashboards/ - nothing to import).

  Reading the panels:
    - "Support turns completed / min" - overall throughput. Should climb
      while turns are running, then flatten once NUM_TURNS is reached.
    - "Turns by resolved intent" - which categories classify_intent has been
      routing to across all turns so far (a pie, not a time series, since
      it's a cumulative Counter).
    - "p95 node latency" - one line per LangGraph node. generate_response
      should sit well above classify_intent, which should sit well above
      retrieve_policy_context (a dict lookup, no network call) - the same
      shape 17_2's waterfall showed for one trace, now as a trend across many.
    - "p95 full turn latency" / "Node errors (5m)" - single-number health
      checks, the kind you'd actually put on an alert rule in a real system.
    - "LLM token usage rate" - input vs output tokens burned per node, per
      second - the metric a cost dashboard would actually chart.
  3. You can also query the raw numbers directly at http://localhost:9095
     (Prometheus's own UI, under Graph) - e.g. paste in
     `securelife_agent_requests_total` - or check Status -> Targets there to
     confirm the securelife-insurance-agent scrape target shows "UP". (Host port
     9095, not Prometheus's usual 9090 - see docker-compose.yml for why.)
"""


if __name__ == "__main__":
    try:
        start_http_server(METRICS_PORT)
        print(f"[ok] Metrics server listening at http://localhost:{METRICS_PORT}/metrics")
    except OSError as exc:
        print(f"[error] Could not bind port {METRICS_PORT} - is another instance of this script "
              f"already running? ({exc})")
        raise SystemExit(1)

    query_cycle = itertools.cycle(DEMO_QUERIES)

    for i in range(NUM_TURNS):
        session_id = f"sess-{i:03d}"
        query = next(query_cycle)
        banner(f"TURN {i + 1}/{NUM_TURNS} - SESSION {session_id}: {query!r}")
        answer = run_support_turn(query)
        print(f"\n  [final response] {answer}")
        if i < NUM_TURNS - 1:
            time.sleep(SLEEP_BETWEEN_TURNS_SECONDS)

    banner("HOW TO READ THE GRAFANA DASHBOARD")
    print(HOW_TO_READ_THE_DASHBOARD)
    print(f"  Turns are done - lingering for {LINGER_SECONDS}s so Prometheus keeps scraping a live "
          f"target while you look at the dashboard. Ctrl+C to exit sooner.")
    try:
        time.sleep(LINGER_SECONDS)
    except KeyboardInterrupt:
        pass
    print("\n  Done - the containers (docker compose) keep running with the last-scraped data until "
          "you stop them with `docker compose down` from the monitoring/ folder.")
