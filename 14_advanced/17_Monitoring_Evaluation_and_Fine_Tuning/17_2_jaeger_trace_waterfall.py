import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")

import os
import sys
from typing import Literal, TypedDict
import requests
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import Status, StatusCode

load_dotenv(override=True)
sys.stdout.reconfigure(encoding="utf-8")

# Same "some other tool already disabled OpenTelemetry" defensive fix carried over
# from 17_1_opentelemetry_langgraph.py - see that file's header comment for why.
os.environ["OTEL_SDK_DISABLED"] = "false"
os.environ["OTEL_TRACES_SAMPLER"] = "always_on"

# =====================================================================
# 17_1 exported spans as raw JSON, to a console and a file - readable, but
# you're manually eyeballing timestamps to figure out what overlapped what.
# This file exports the SAME instrumented LangGraph agent's spans to
# JAEGER instead, and the payoff is a WATERFALL VIEW you can actually read
# at a glance: bars stacked by parent/child, positioned left-to-right by
# start time, width = duration, red = error. This is the whole reason
# distributed tracing tools exist - see "HOW TO READ THE WATERFALL" at the
# bottom of this file (and printed at the end of the run) for what to look
# for once it's open.
#
# SETUP - run Jaeger locally with its all-in-one image. Modern Jaeger
# (>=1.35) accepts OpenTelemetry's OTLP protocol NATIVELY - no separate
# "Jaeger exporter" package, no collector/agent sidecar, just point an
# OTLPSpanExporter at it:
#
#   docker run -d --name jaeger --rm ^
#     -p 16686:16686 -p 4317:4317 -p 4318:4318 ^
#     jaegertracing/all-in-one:latest
#
#   pip install opentelemetry-exporter-otlp-proto-http
#
# Ports: 16686 = web UI, 4318 = OTLP/HTTP (used below), 4317 = OTLP/gRPC
# (swap in opentelemetry.exporter.otlp.proto.grpc.trace_exporter.OTLPSpanExporter
# and endpoint "localhost:4317" if you'd rather use gRPC).
#
# PROCESSOR: 17_1 used a SimpleSpanProcessor (exports synchronously, the
# instant a span ends - fine when the "exporter" is a print statement).
# Here we switch to a BatchSpanProcessor, which is what you'd actually use
# in production: it buffers spans and ships them in batches on a
# background thread so tracing never blocks the request path. The
# tradeoff, and a real gotcha for a short-lived script like this one: that
# background thread might not have flushed its buffer yet by the time the
# process exits, silently dropping the last batch - which is why the
# `finally` block below calls `provider.shutdown()` (which flushes first)
# BEFORE the script exits, not just for tidiness like it was in 17_1.
# =====================================================================

JAEGER_UI_URL = "http://localhost:16686"
JAEGER_OTLP_HTTP_ENDPOINT = "http://localhost:4318/v1/traces"


def jaeger_is_reachable() -> bool:
    try:
        requests.get(JAEGER_UI_URL, timeout=1.5)
        return True
    except requests.exceptions.RequestException:
        return False


resource = Resource.create({"service.name": "securelife-insurance-agent", "service.version": "1.0.0"})
provider = TracerProvider(resource=resource)
provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=JAEGER_OTLP_HTTP_ENDPOINT)))
trace.set_tracer_provider(provider)  # best-effort; harmless if something else already claimed the global slot
tracer = provider.get_tracer("securelife.insurance_agent")  # get it from OUR provider either way - see 17_1

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
    with tracer.start_as_current_span("classify_intent") as span:
        span.set_attribute("gen_ai.system", "openai")
        span.set_attribute("gen_ai.request.model", "gpt-4o-mini")
        span.set_attribute("gen_ai.operation.name", "chat")

        result = intent_llm.invoke(
            "Classify this SecureLife customer message into exactly one category - "
            f"claim_status, coverage_question, or general: {state['query']!r}"
        )
        parsed: IntentResult = result["parsed"]
        usage = getattr(result["raw"], "usage_metadata", None) or {}

        span.set_attribute("gen_ai.usage.input_tokens", usage.get("input_tokens", 0))
        span.set_attribute("gen_ai.usage.output_tokens", usage.get("output_tokens", 0))
        span.set_attribute("securelife.intent", parsed.intent)

        return {"intent": parsed.intent}


def retrieve_policy_context(state: SupportState) -> SupportState:
    with tracer.start_as_current_span("retrieve_policy_context") as span:
        span.set_attribute("securelife.intent", state["intent"])

        article = SECURELIFE_KB.get(state["intent"])
        if article:
            span.set_attribute("securelife.kb.hit", True)
            span.set_attribute("securelife.kb.article_id", state["intent"])
        else:
            span.set_attribute("securelife.kb.hit", False)
            span.add_event("kb_miss", {"securelife.intent": state["intent"]})

        return {"context": article or "No specific KB article - answer from general policy knowledge."}


def generate_response(state: SupportState) -> SupportState:
    with tracer.start_as_current_span("generate_response") as span:
        span.set_attribute("gen_ai.system", "openai")
        span.set_attribute("gen_ai.request.model", "gpt-4o-mini")
        span.set_attribute("gen_ai.operation.name", "chat")

        messages = [
            SystemMessage(
                content=(
                    "You are Meera, SecureLife Insurance's customer support agent. "
                    f"Relevant reference material: {state['context']}"
                )
            ),
            HumanMessage(content=state["query"]),
        ]
        try:
            ai_message = llm.invoke(messages)
        except Exception as exc:
            span.record_exception(exc)
            span.set_status(Status(StatusCode.ERROR, str(exc)))
            raise

        usage = ai_message.usage_metadata or {}
        span.set_attribute("gen_ai.usage.input_tokens", usage.get("input_tokens", 0))
        span.set_attribute("gen_ai.usage.output_tokens", usage.get("output_tokens", 0))
        span.set_attribute(
            "gen_ai.response.finish_reasons", [ai_message.response_metadata.get("finish_reason", "unknown")]
        )

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


def run_support_turn(session_id: str, query: str) -> str:
    with tracer.start_as_current_span("securelife_support_turn") as root_span:
        root_span.set_attribute("securelife.session_id", session_id)
        root_span.set_attribute("securelife.query_length", len(query))
        result = app.invoke({"query": query, "intent": "", "context": "", "response": ""})
        return result["response"]


def banner(title: str) -> None:
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


HOW_TO_READ_THE_WATERFALL = f"""
  1. Open {JAEGER_UI_URL} in a browser.
  2. Service dropdown -> "securelife-insurance-agent" -> Find Traces.
  3. Click the most recent "securelife_support_turn" trace.

  Reading the waterfall:
    - The TOP bar (securelife_support_turn) spans the full width - that's
      the total latency of one support turn, start to finish.
    - Each child bar's LEFT EDGE = when that node started, offset from the
      trace's start; its WIDTH = how long it took. This graph is strictly
      sequential (classify_intent -> retrieve_policy_context ->
      generate_response), so the three bars sit end-to-end with no
      overlap. If two bars overlapped horizontally, that would mean two
      nodes ran concurrently - a fan-out/parallel branch, not a bug.
    - generate_response is almost always the widest bar: it's the node
      making the real LLM call with the fullest prompt.
    - retrieve_policy_context should be a barely-visible sliver - it's a
      dict lookup, not a network call, and the waterfall makes that cost
      difference visually obvious in a way scrolling through logs never
      does.
    - Any gap BETWEEN bars is LangGraph/Python overhead that never got its
      own span - real, but currently invisible; wrap it in its own span if
      it ever needs explaining.
  4. Click any span to open its TAGS panel - every set_attribute() call
     from the code (gen_ai.usage.input_tokens, securelife.intent,
     securelife.kb.hit, ...) shows up there.
  5. A RED span means it errored - open its LOGS to see the recorded
     exception (the same record_exception()/set_status() call from 17_1,
     now rendered by a real UI instead of raw JSON).
"""


if __name__ == "__main__":
    if jaeger_is_reachable():
        print(f"[ok] Jaeger UI reachable at {JAEGER_UI_URL}")
    else:
        print(f"[warning] Could not reach {JAEGER_UI_URL} - is the Jaeger container running? See the SETUP")
        print("          comment at the top of this file for the `docker run` command. Continuing anyway -")
        print("          the OTLP exporter will just fail to deliver spans in the background (BatchSpanProcessor")
        print("          swallows export errors rather than crashing the script), so the agent itself still works.")

    turns = [
        ("sess-001", "How long does it take for a claim to be reviewed?"),
        ("sess-002", "Is my pre-existing diabetes covered after 3 years on the policy?"),
        ("sess-003", "What are your office hours?"),
    ]

    try:
        for session_id, query in turns:
            banner(f"SESSION {session_id}: {query!r}")
            answer = run_support_turn(session_id, query)
            print(f"\n  [final response] {answer}")
    finally:
        # Unlike 17_1's SimpleSpanProcessor, THIS shutdown() is load-bearing: it
        # flushes the BatchSpanProcessor's buffer before the process exits, so the
        # final batch of spans actually reaches Jaeger instead of being dropped.
        provider.shutdown()

    banner("HOW TO READ THIS TRACE IN JAEGER")
    print(HOW_TO_READ_THE_WATERFALL)
