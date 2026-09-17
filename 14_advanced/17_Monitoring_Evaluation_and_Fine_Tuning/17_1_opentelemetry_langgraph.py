import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")

import os
import sys
from typing import Literal, TypedDict
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import SpanProcessor, TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor
from opentelemetry.trace import Status, StatusCode

load_dotenv(override=True)
sys.stdout.reconfigure(encoding="utf-8")

# Zero spans captured with NO exceptions anywhere (confirmed by testing) points at
# one specific culprit: OpenTelemetry's own kill switches, read from the OS
# environment - NOT this repo's .env - at the moment a TracerProvider is built.
# `OTEL_SDK_DISABLED=true` (or an `OTEL_TRACES_SAMPLER` that drops everything) is a
# very common default set machine-wide by corporate APM agents, VPN/security
# software, or other dev tools, and it silently makes every span a no-op: no error,
# attributes just get dropped, nothing ever reaches a processor. This is exactly
# what "no exception but zero spans, even for a bare module-level span" looks like.
# Force both off/on for THIS process so the demo can't be silently disabled by
# something unrelated already sitting in the environment.
print(f"[diagnostic] OTEL_SDK_DISABLED was: {os.environ.get('OTEL_SDK_DISABLED')!r}")
print(f"[diagnostic] OTEL_TRACES_SAMPLER was: {os.environ.get('OTEL_TRACES_SAMPLER')!r}")
os.environ["OTEL_SDK_DISABLED"] = "false"
os.environ["OTEL_TRACES_SAMPLER"] = "always_on"

# =====================================================================
# OpenTelemetry for AI: instrumenting a LangGraph agent with SPANS and
# ATTRIBUTES.
#
#   Trace     - the end-to-end record of one agent run (here, one
#               SecureLife support turn), made up of...
#   Span      - ...a timed unit of work inside that trace. Spans NEST:
#               a "root" span for the whole turn, with a "child" span
#               per LangGraph node, gives you a waterfall exactly like
#               a call stack, but with wall-clock durations attached.
#   Attribute - a key/value fact recorded ON a span (which model, how
#               many tokens, which intent was matched, whether a KB
#               lookup hit or missed, ...) - this is what turns "the
#               agent was slow" into "classify_intent took 900ms and
#               burned 400 output tokens because it was fed an
#               oversized system prompt", i.e. the metrics slide181
#               lists a production dashboard as wanting: prompt/token
#               usage, model selection, latency, tool-call success,
#               agent execution path.
#
# Everything below is instrumented BY HAND with the OpenTelemetry SDK
# directly (no auto-instrumentation library) so every span/attribute
# call is visible. The `gen_ai.*` attribute names on the LLM spans
# follow OpenTelemetry's own semantic conventions for generative AI,
# so a real backend (Jaeger, Honeycomb, Datadog, ...) would render them
# the same way any other OTel-instrumented GenAI call shows up.
#
# EXPORTER: a `ConsoleSpanExporter` just pretty-prints each span as
# JSON to stdout the moment it ends - zero external infra, perfect for
# a self-contained script. In production you'd swap it for an
# `OTLPSpanExporter` pointed at a collector and use a `BatchSpanProcessor`
# (buffers spans, exports off the hot path) instead of the
# `SimpleSpanProcessor` used here (exports synchronously - fine for a
# short demo, adds latency to every span in a real service).
#
# That raw JSON dump IS the tracing - it's just verbose (one multi-line
# block per span, printed the instant that span ends, interleaved with
# everything else the script prints) so it's easy to lose in scrollback -
# or in a terminal/IDE setup that swallows a third-party library's direct
# writes to stdout entirely. So the SAME JSON is also written to a plain
# file on disk (TRACE_LOG_PATH below) via a second ConsoleSpanExporter
# pointed at that file instead of stdout - `ConsoleSpanExporter` just
# formats a span as JSON and writes it to whatever `out` file-like object
# you give it, so it doubles as a "dump spans to a file" exporter for
# free. `TraceSummaryCollector` below adds a THIRD span processor that
# buffers ended spans in memory so we can also print/write a short
# one-line-per-span waterfall after each turn - a human-readable recap
# of the exact same data.
# =====================================================================

TRACE_LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "otel_trace_output.log")
trace_log_file = open(TRACE_LOG_PATH, "w", encoding="utf-8")

resource = Resource.create({"service.name": "securelife-insurance-agent", "service.version": "1.0.0"})
provider = TracerProvider(resource=resource)
provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))  # raw JSON -> stdout
provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter(out=trace_log_file)))  # same JSON -> file


class TraceSummaryCollector(SpanProcessor):
    def __init__(self) -> None:
        self._spans_by_trace: dict[int, list] = {}

    def on_end(self, span) -> None:
        self._spans_by_trace.setdefault(span.context.trace_id, []).append(span)

    def spans_for_trace(self, trace_id: int) -> list:
        return sorted(self._spans_by_trace.get(trace_id, []), key=lambda s: s.start_time)


trace_summary_collector = TraceSummaryCollector()
provider.add_span_processor(trace_summary_collector)

# GOTCHA: opentelemetry.trace.set_tracer_provider() sets a PROCESS-WIDE global that
# can only ever be set ONCE - if anything else in this process (LangSmith, Langfuse,
# and others now instrument themselves with OpenTelemetry too, and this repo's .env
# has LANGSMITH_TRACING=true) claims that slot first, our call here is silently
# ignored and trace.get_tracer(...) would hand back a tracer bound to THEIR
# provider - meaning spans would be created and attributes set with no error, but
# never reach our ConsoleSpanExporter or TraceSummaryCollector at all. Getting the
# tracer straight from OUR OWN provider instance sidesteps that contest entirely.
trace.set_tracer_provider(provider)  # best-effort global registration; harmless if ignored
tracer = provider.get_tracer("securelife.insurance_agent")

# Self-test: prove the pipeline works BEFORE any LangGraph/LLM code runs at all, so
# a zero count later can't be blamed on threading, LangGraph, or the LLM call path.
with tracer.start_as_current_span("startup_self_test") as _self_test_span:
    print(f"[diagnostic] self-test span.is_recording() = {_self_test_span.is_recording()}")
_self_test_count = sum(len(spans) for spans in trace_summary_collector._spans_by_trace.values())
print(f"[diagnostic] spans captured right after self-test span ended: {_self_test_count}")


def print_trace_waterfall(trace_id: int) -> None:
    lines = ["\n  --- trace waterfall (readable recap of the JSON spans above) ---"]
    for span in trace_summary_collector.spans_for_trace(trace_id):
        duration_ms = (span.end_time - span.start_time) / 1_000_000
        attrs = ", ".join(f"{k}={v}" for k, v in span.attributes.items()) if span.attributes else ""
        lines.append(f"  [{duration_ms:7.1f}ms] {span.name:<24} {attrs}")
    for line in lines:
        print(line)
        print(line, file=trace_log_file)
    trace_log_file.flush()

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

        # include_raw=True hands back BOTH the raw AIMessage (which carries token
        # usage) and the parsed Pydantic object - structured output would otherwise
        # throw the usage numbers away.
        span.set_attribute("gen_ai.usage.input_tokens", usage.get("input_tokens", 0))
        span.set_attribute("gen_ai.usage.output_tokens", usage.get("output_tokens", 0))
        span.set_attribute("securelife.intent", parsed.intent)

        return {"intent": parsed.intent}


def retrieve_policy_context(state: SupportState) -> SupportState:
    # A plain (non-LLM) span - not every node in an agent graph calls a model, and
    # a trace should show that: this hop is a dict lookup, not an API round trip.
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
            # start_as_current_span() already auto-records an uncaught exception and
            # marks the span ERROR when it propagates out of the `with` block (that's
            # why classify_intent's span above shows ERROR too, with no try/except at
            # all) - this explicit version is only here to set a clearer status
            # description than the default repr() would give.
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
    # The ROOT span for the whole turn - every node span above is created while
    # this one is "current", so OpenTelemetry nests them under it automatically.
    with tracer.start_as_current_span("securelife_support_turn") as root_span:
        root_span.set_attribute("securelife.session_id", session_id)
        # Log the query's LENGTH, not its raw text, as a span attribute - attributes
        # are exported to a tracing backend just like any other telemetry, so the
        # same "don't leak PII" discipline from 16_3_presidio.py applies here too.
        root_span.set_attribute("securelife.query_length", len(query))

        result = app.invoke({"query": query, "intent": "", "context": "", "response": ""})
        print_trace_waterfall(root_span.get_span_context().trace_id)
        return result["response"]


def banner(title: str) -> None:
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


if __name__ == "__main__":
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
        # SimpleSpanProcessor already exported every span synchronously as it ended,
        # so this shutdown+close is just tidy cleanup, not a requirement for spans to
        # appear - but it's in a `finally` so the file still gets flushed/closed even
        # if a turn above raised (e.g. an API error mid-run).
        provider.shutdown()
        total_spans = sum(len(spans) for spans in trace_summary_collector._spans_by_trace.values())
        trace_log_file.close()
        banner("TRACE OUTPUT")
        print(f"  Spans captured this run : {total_spans}")
        print(f"  Full JSON log written to: {TRACE_LOG_PATH}")
        if total_spans == 0:
            print("  No spans were captured at all - open the file above (it will be empty) "
                  "and double check no exception happened before any node ran.")
