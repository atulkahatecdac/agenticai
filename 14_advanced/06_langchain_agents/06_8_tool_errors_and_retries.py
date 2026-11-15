import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

import sys
from collections import Counter
from dotenv import load_dotenv
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

load_dotenv(override=True)
sys.stdout.reconfigure(encoding="utf-8")

# =====================================================================
# Tools fail. An agent that crashes on the first error is a demo, not a
# product. Four layers of defence, from the inside out:
#
#   1. Retry TRANSIENT errors inside the tool (timeouts, 503s) with
#      exponential backoff - the LLM never even sees them.
#   2. Return PERMANENT errors (bad arguments) to the LLM as the tool
#      result, with a hint, so it can correct itself and try again.
#   3. Retry the LLM call itself and fall back to a second model.
#   4. A circuit breaker: stop calling a tool that keeps failing, and a
#      step limit so the loop always ends.
# =====================================================================


class TransientError(Exception):
    """A failure worth retrying: timeout, rate limit, 503."""


# ---------------------------------------------------------------------
# Layer 1: a flaky "exchange-rate service" - the first two calls time
# out. @retry tries again after 0.5 s, then 1 s; the third call works.
# ---------------------------------------------------------------------
RATES = {"USD": 1.0, "INR": 88.2, "EUR": 0.86, "GBP": 0.75, "JPY": 151.0}
_calls = Counter()


@retry(
    retry=retry_if_exception_type(TransientError),   # only retry what is worth retrying
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=0.5, max=4),
    before_sleep=lambda rs: print(f"   [retry] attempt {rs.attempt_number} failed: {rs.outcome.exception()} - waiting"),
    reraise=True,
)
def fetch_rate(currency: str) -> float:
    _calls[currency] += 1
    if _calls[currency] <= 2:
        raise TransientError("exchange-rate service timed out")
    return RATES[currency]


@tool
def convert_currency(amount: float, from_code: str, to_code: str) -> str:
    """Convert an amount between currencies. from_code and to_code must be
    3-letter ISO codes: USD, INR, EUR, GBP or JPY."""
    # Layer 2: validate and explain. ValueError -> goes back to the LLM.
    for code in (from_code, to_code):
        if code not in RATES:
            raise ValueError(
                f"'{code}' is not a supported ISO currency code. Use one of {sorted(RATES)} "
                "(for example rupees -> INR)."
            )
    usd = amount / fetch_rate(from_code)
    return f"{amount:,.2f} {from_code} = {usd * fetch_rate(to_code):,.2f} {to_code}"


@tool
def get_shipping_quote(country: str) -> str:
    """Get the shipping cost in USD to a country."""
    raise ConnectionError("shipping API is down")   # always fails - see the circuit breaker


tools = [convert_currency, get_shipping_quote]
tools_by_name = {t.name: t for t in tools}

# ---------------------------------------------------------------------
# Layer 3: retry the LLM call on errors (network, 429, 5xx), and fall
# back to another model if the first keeps failing.
# ---------------------------------------------------------------------
primary = ChatOpenAI(model="gpt-4o-mini", temperature=0, max_retries=0).bind_tools(tools)
backup = ChatOpenAI(model="gpt-4.1-mini", temperature=0, max_retries=0).bind_tools(tools)
llm = primary.with_retry(stop_after_attempt=3, wait_exponential_jitter=True).with_fallbacks([backup])

SYSTEM = (
    "You help online shoppers. Use the tools for every number. If a tool returns an error, "
    "read it, fix your arguments and try again. If a tool is unavailable, say so and carry on "
    "with what you can answer."
)


# ---------------------------------------------------------------------
# The agent loop from 06_3, plus error handling and Layer 4.
# ---------------------------------------------------------------------
def run_agent(question: str, max_steps: int = 8, max_failures_per_tool: int = 2) -> str:
    messages: list[BaseMessage] = [SystemMessage(SYSTEM), HumanMessage(question)]
    failures = Counter()

    for step in range(1, max_steps + 1):
        ai = llm.invoke(messages)
        messages.append(ai)
        if not ai.tool_calls:
            return ai.content

        for call in ai.tool_calls:
            name = call["name"]
            print(f"[step {step}] {name}({call['args']})")
            if failures[name] >= max_failures_per_tool:          # circuit open: don't even try
                result = f"Error: {name} is unavailable right now. Do not call it again."
            else:
                try:
                    result = tools_by_name[name].invoke(call["args"])
                except ValueError as e:                            # the LLM can fix this
                    result = f"Error: {e}"
                    failures[name] += 1
                except Exception as e:                             # the LLM cannot fix this
                    result = f"Error: {name} failed ({type(e).__name__}: {e})."
                    failures[name] += 1
            print(f"         -> {result}")
            messages.append(ToolMessage(content=str(result), tool_call_id=call["id"]))

    return f"Stopped after {max_steps} steps without a final answer."


if __name__ == "__main__":
    # Layer 2 on its own: this is the tool result the LLM gets back when it
    # passes a currency NAME instead of a code - it says what to send instead.
    print("Layer 2 - what the LLM sees after a bad argument:")
    try:
        convert_currency.invoke({"amount": 120, "from_code": "euros", "to_code": "rupees"})
    except ValueError as e:
        print(f"   Error: {e}\n")

    question = (
        "I want to buy a jacket that costs 120 euros. How much is that in rupees? "
        "Also, what would shipping cost to India, to Japan and to the UK?"
    )
    print("QUESTION:", question, "\n")
    answer = run_agent(question)
    print("\n" + "=" * 70)
    print("FINAL ANSWER\n" + "=" * 70)
    print(answer)
    print("\nWatch for: [retry] lines (layer 1 - the LLM never sees them), and the shipping")
    print("tool being cut off after two failures (layer 4) - the third country is never tried.")
