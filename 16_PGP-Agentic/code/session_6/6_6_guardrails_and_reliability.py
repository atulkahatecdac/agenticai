import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

import re
import sys
import yfinance as yf
from dotenv import load_dotenv
from crewai import Agent, Task, Crew
from crewai.tasks.task_output import TaskOutput
from crewai.tools import tool

load_dotenv(override=True)
sys.stdout.reconfigure(encoding="utf-8")

# =====================================================================
# Guardrails, error handling and reliability. Agents fail in specific
# ways: hallucinating, returning incomplete info, producing invalid
# output, or hitting an external service that's down. Two different
# layers of defense against that, shown together here:
#
#   1. TOOL-level error handling: get_stock_snapshot() below never
#      raises on a bad ticker or a Yahoo Finance hiccup - it returns a
#      plain "no data found" string, so one bad tool call can't crash
#      the whole crew.
#   2. TASK-level guardrail: Task(guardrail=...) is a Python callable
#      that checks the agent's OUTPUT before the task is accepted -
#      format (states a real verdict), quality (has actual reasoning,
#      not a one-liner), and a safety/factual check (any $-price the
#      agent claims must be close to the REAL price - catching
#      hallucinated numbers). A failing guardrail sends the agent the
#      error and lets it retry, up to guardrail_max_retries.
# =====================================================================


@tool("StockSnapshot")
def get_stock_snapshot(ticker: str) -> str:
    """Fetch a live snapshot of key financial metrics for a stock ticker from Yahoo Finance."""
    try:
        info = yf.Ticker(ticker).info
    except Exception as exc:
        return f"Yahoo Finance lookup failed for '{ticker}': {exc}"
    if not info or info.get("shortName") is None:
        return f"No data found for ticker '{ticker}'."
    return (
        f"{info.get('shortName')} ({ticker.upper()})\n"
        f"Current price: {info.get('currentPrice', info.get('regularMarketPrice', 'n/a'))}\n"
        f"Trailing P/E: {info.get('trailingPE', 'n/a')}\n"
        f"Analyst mean target: {info.get('targetMeanPrice', 'n/a')}"
    )


def make_recommendation_guardrail(real_price: float | None):
    def guardrail(output: TaskOutput) -> tuple[bool, str]:
        text = output.raw
        lower = text.lower()

        # Content check: must state a clear verdict
        if not any(word in lower for word in ("buy", "hold", "sell")):
            return False, "Output must explicitly state buy, hold, or sell."

        # Quality check: must include actual reasoning, not a one-word verdict
        if len(text.strip()) < 40:
            return False, "Output is too short - include supporting reasoning, not just a verdict."

        # Safety/factual check: any $-price claimed must be close to the REAL price
        claimed_prices = [float(p) for p in re.findall(r"\$?(\d+(?:\.\d+)?)\s*(?:USD|dollars)?", text)]
        if real_price:
            for price in claimed_prices:
                if price > 1 and abs(price - real_price) / real_price > 0.5:
                    return False, (
                        f"Claimed price {price} looks hallucinated - the real current "
                        f"price is {real_price:.2f}. Re-check your numbers against the tool output."
                    )

        return True, text

    return guardrail


trader = Agent(
    role="Trade Recommendation Agent",
    goal="Give a buy/hold/sell recommendation grounded strictly in real tool data",
    backstory="You never state a price you didn't get from the StockSnapshot tool.",
    tools=[get_stock_snapshot],
    llm="gpt-4o-mini",
    verbose=True,
)

if __name__ == "__main__":
    ticker = "AMZN"
    info = yf.Ticker(ticker).info
    real_price = info.get("currentPrice") or info.get("regularMarketPrice")
    print(f"[reliability check] real current price for {ticker}: {real_price}\n")

    recommendation_task = Task(
        description=(
            f"Fetch the snapshot for {ticker} using the StockSnapshot tool, then give a "
            "buy/hold/sell recommendation with supporting reasoning, citing the current price."
        ),
        expected_output="A buy/hold/sell recommendation with reasoning, citing the real current price",
        agent=trader,
        guardrail=make_recommendation_guardrail(real_price),
        guardrail_max_retries=3,
    )

    crew = Crew(agents=[trader], tasks=[recommendation_task], verbose=True)
    result = crew.kickoff()

    print("\n" + "=" * 70)
    print("GUARDRAIL-VALIDATED RECOMMENDATION")
    print("=" * 70)
    print(result)

    print("\n" + "=" * 70)
    print("TOOL-LEVEL RELIABILITY: a bad ticker doesn't crash anything")
    print("=" * 70)
    print(get_stock_snapshot.run(ticker="NOT_A_REAL_TICKER_XYZ"))
