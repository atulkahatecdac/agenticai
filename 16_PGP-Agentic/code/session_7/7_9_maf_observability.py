# Microsoft Agent Framework (MAF) - SecureBank: tracing with OpenTelemetry.
# Every Agent is already instrumented. configure_otel_providers() switches the traces on;
# here a console exporter prints one compact line per span:
#   invoke_agent <name>   - the whole agent run
#   chat <model>          - each LLM call (with token counts)
#   execute_tool <name>   - each tool call
# To see the same trace as a waterfall, run Jaeger (see 14_advanced/17_Monitoring_Evaluation_and_Fine_Tuning)
# and set OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317 instead of using the console exporter.
#
# pip install agent-framework-core agent-framework-openai python-dotenv opentelemetry-sdk
# Needs OPENAI_API_KEY in .env

import asyncio
import os
from typing import Annotated

from agent_framework import Agent, tool
from agent_framework.observability import configure_otel_providers, get_tracer
from agent_framework.openai import OpenAIChatCompletionClient
from dotenv import load_dotenv
from opentelemetry import trace
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import ConsoleSpanExporter

load_dotenv(override=True)

# OTEL_SDK_DISABLED=true (often set machine-wide to silence CrewAI's telemetry) turns every
# OpenTelemetry tracer into a no-op, so this demo would record nothing. Re-enable it for this process.
os.environ["OTEL_SDK_DISABLED"] = "false"


def one_line(span: ReadableSpan) -> str:
    """Print a span as: name, duration, tokens in/out (instead of the default 40-line JSON)."""
    ms = (span.end_time - span.start_time) / 1e6
    tokens_in = span.attributes.get("gen_ai.usage.input_tokens")
    tokens_out = span.attributes.get("gen_ai.usage.output_tokens")
    tokens = f"  tokens {tokens_in}/{tokens_out}" if tokens_in is not None else ""
    return f"  {span.name:30} {ms:6.0f} ms{tokens}\n"


configure_otel_providers(exporters=[ConsoleSpanExporter(formatter=one_line)])


@tool
def get_balance(account_id: Annotated[str, "SecureBank account id, e.g. ACC-1001"]) -> str:
    """Return the current balance (INR) of a SecureBank account."""
    return f"{account_id}: INR 1,25,000.00"


@tool
def get_recent_transactions(account_id: Annotated[str, "SecureBank account id"]) -> str:
    """Return the last three transactions of a SecureBank account."""
    return "12 Nov: Swiggy -450 | 11 Nov: Salary +1,10,000 | 10 Nov: Amazon -2,999"


agent = Agent(
    OpenAIChatCompletionClient(model="gpt-4o-mini"),
    name="bank_assistant",
    instructions="You are SecureBank's assistant. Use the tools.",
    tools=[get_balance, get_recent_transactions],
)


async def main():
    # A custom parent span groups everything that happens for one customer request
    
    with get_tracer().start_as_current_span("customer_request ACC-1001"):
        result = await agent.run("What's my balance on ACC-1001 and what did I spend on recently?")

    # Spans are exported in batches (normally at exit); flush now so the trace prints first.
    # Children finish before their parent, so the list reads inside-out.
    print("TRACE (span, duration, tokens in/out):")
    trace.get_tracer_provider().force_flush()
    print("\nAGENT:", result.text)


if __name__ == "__main__":
    asyncio.run(main())
