import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

import sys
import yfinance as yf
from dotenv import load_dotenv
from crewai import Agent, Task, Crew
from crewai.tools import tool

load_dotenv(override=True)
sys.stdout.reconfigure(encoding="utf-8")

# =====================================================================
# Human-in-the-loop (HITL) and controlled autonomy: not every agent
# decision should ship without a human checking it first. CrewAI's
# Task(human_input=True) pauses after that task runs and asks a human,
# in the terminal, to approve or give feedback before the crew moves
# on - the agent then revises its output based on that feedback.
#
# Three levels of autonomy (least to most autonomous):
#   - human-in-the-loop:     a human must approve before the action
#                             ships (this demo - a trade recommendation)
#   - human-on-the-loop:     a human supervises/monitors but doesn't
#                             block each action (e.g. a review dashboard)
#   - human-out-of-the-loop: fully autonomous, no human checkpoint
#                             (e.g. 6_2's snapshot summary - low stakes)
# A buy/sell recommendation has real consequences if wrong, so it gets
# the strictest level here: human-in-the-loop.
# =====================================================================


@tool("StockSnapshot")
def get_stock_snapshot(ticker: str) -> str:
    """Fetch a live snapshot of key financial metrics for a stock ticker from Yahoo Finance."""
    info = yf.Ticker(ticker).info
    if not info or info.get("shortName") is None:
        return f"No data found for ticker '{ticker}'."
    return (
        f"{info.get('shortName')} ({ticker.upper()})\n"
        f"Price: {info.get('currentPrice', info.get('regularMarketPrice', 'n/a'))}\n"
        f"Trailing P/E: {info.get('trailingPE', 'n/a')}\n"
        f"Revenue growth (YoY): {info.get('revenueGrowth', 'n/a')}\n"
        f"Analyst recommendation: {info.get('recommendationKey', 'n/a')} "
        f"(mean target: {info.get('targetMeanPrice', 'n/a')})"
    )


trader = Agent(
    role="Trade Recommendation Agent",
    goal="Propose a buy/hold/sell recommendation grounded in live data",
    backstory="You propose clear trade recommendations, but you know a human must sign off before they're final.",
    tools=[get_stock_snapshot],
    llm="gpt-4o-mini",
    verbose=True,
)

recommendation_task = Task(
    description="Fetch the snapshot for {ticker} and propose a buy/hold/sell recommendation with reasoning.",
    expected_output="A buy/hold/sell recommendation with supporting reasoning",
    agent=trader,
    human_input=True,  # human-in-the-loop: pauses for approval/feedback before this task is done
)

crew = Crew(
    agents=[trader],
    tasks=[recommendation_task],
    verbose=True,
)

if __name__ == "__main__":
    print("This demo will pause and ask YOU (in the terminal) to approve or")
    print("give feedback on the agent's trade recommendation before it finalizes.\n")
    result = crew.kickoff(inputs={"ticker": "GOOGL"})
    print("\n" + "=" * 70)
    print("FINAL, HUMAN-APPROVED RECOMMENDATION")
    print("=" * 70)
    print(result)
