import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

import sys
import yfinance as yf
from dotenv import load_dotenv
from crewai import Agent, Task, Crew
from crewai.tools import tool
from crewai.memory import EntityMemory

load_dotenv(override=True)
sys.stdout.reconfigure(encoding="utf-8")

# =====================================================================
# Context and memory in CrewAI, on a two-agent crew:
#
#   Context - passes one task's output into another task IN THE SAME RUN.
#             brief_task has context=[fetch_task], so the writer receives
#             the analyst's snapshot. (In a sequential crew this happens
#             implicitly too; context= makes it explicit and lets a task
#             pick exactly which earlier tasks it sees.)
#
#   Memory  - carries what the crew learned ACROSS RUNS.
#             memory=True stores results (short-term, long-term, entity
#             memory) so the second kickoff (MSFT) can recall the first
#             one (AAPL) and compare. The MSFT run only fetches MSFT data,
#             so Apple's numbers in its brief can only come from memory.
#             Memory search is semantic with a relevance cut-off: CrewAI
#             drops matches scoring below 0.6, and the stored Apple facts
#             score ~0.5 here - so nothing would be recalled. RecallEntityMemory
#             below lowers the cut-off to 0.45 so they get through.
#
# Data is live from Yahoo Finance via yfinance.
# =====================================================================


@tool("StockSnapshot")
def get_stock_snapshot(ticker: str) -> str:
    """Fetch a live snapshot of key financial metrics for a stock ticker from Yahoo Finance."""
    info = yf.Ticker(ticker).info
    if not info or info.get("shortName") is None:
        return f"No data found for ticker '{ticker}'."
    return (
        f"{info.get('shortName')} ({ticker.upper()})\n"
        f"Sector: {info.get('sector', 'n/a')} | Industry: {info.get('industry', 'n/a')}\n"
        f"Price: {info.get('currentPrice', info.get('regularMarketPrice', 'n/a'))}\n"
        f"Trailing P/E: {info.get('trailingPE', 'n/a')} | Forward P/E: {info.get('forwardPE', 'n/a')}\n"
        f"Revenue growth (YoY): {info.get('revenueGrowth', 'n/a')}\n"
        f"Profit margin: {info.get('profitMargins', 'n/a')}\n"
        f"52-week range: {info.get('fiftyTwoWeekLow', 'n/a')} - {info.get('fiftyTwoWeekHigh', 'n/a')}\n"
        f"Analyst recommendation: {info.get('recommendationKey', 'n/a')} "
        f"(mean target: {info.get('targetMeanPrice', 'n/a')})"
    )


analyst = Agent(
    role="Financial Data Analyst",
    goal="Fetch and factually summarize a company's current financial snapshot",
    backstory="You pull live market data and report it plainly, without adding opinions.",
    tools=[get_stock_snapshot],
    llm="gpt-4o-mini",
    verbose=True,
)

writer = Agent(
    role="Investment Writer",
    goal="Turn a raw financial snapshot into a short, plain-English brief for a retail investor",
    backstory="You explain financial data clearly, without jargon, in 3-4 sentences.",
    llm="gpt-4o-mini",
    verbose=True,
)

fetch_task = Task(
    description="Fetch the current financial snapshot for {ticker} using the StockSnapshot tool.",
    expected_output="The raw snapshot data for the ticker",
    agent=analyst,
)

brief_task = Task(
    description=(
        "Using the snapshot, write a short plain-English investor brief for {ticker}. "
        "{followup}"
    ),
    expected_output="A 3-4 sentence plain-English summary a non-expert could understand",
    agent=writer,
    context=[fetch_task],   # context: the analyst's output, this run
)

class RecallEntityMemory(EntityMemory):
    """Entity memory (companies, figures, facts) with a lower relevance cut-off."""

    def search(self, query, limit=5, score_threshold=0.45):
        return super().search(query, limit=limit, score_threshold=score_threshold)


crew = Crew(
    agents=[analyst, writer],
    tasks=[fetch_task, brief_task],
    memory=True,                          # memory: carried across kickoffs
    entity_memory=RecallEntityMemory(),
    verbose=True,
)

if __name__ == "__main__":
    crew.reset_memories("all")  # start clean so the demo is repeatable

    runs = [
        ("AAPL", ""),
        ("MSFT", "Then add one sentence comparing it with Apple's profit margin and "
                 "revenue growth from your earlier Apple brief - use the numbers you "
                 "remember, do not look Apple up."),
    ]
    for ticker, followup in runs:
        result = crew.kickoff(inputs={"ticker": ticker, "followup": followup})
        print("\n" + "=" * 70)
        print(f"INVESTOR BRIEF: {ticker}")
        print("=" * 70)
        print(result)
        print()

    print("Apple's numbers in the MSFT brief came from memory - the MSFT run never fetched AAPL.")
