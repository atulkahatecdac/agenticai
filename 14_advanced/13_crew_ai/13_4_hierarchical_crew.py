import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

import sys
import yfinance as yf
from dotenv import load_dotenv
from crewai import Agent, Task, Crew, Process
from crewai.tools import tool

load_dotenv(override=True)
sys.stdout.reconfigure(encoding="utf-8")

# =====================================================================
# Hierarchical crews and manager agents: in a sequential crew, the
# workflow is fixed (Researcher -> Analyst -> Writer, always in that
# order). In a hierarchical crew, a manager agent decides who should
# do what: it understands the objective, delegates sub-questions to
# the right specialist, reviews their results, decides if anything
# needs more work, and coordinates the final output - the manager
# never does the specialist research itself (allow_delegation=True is
# implicit for the manager; CrewAI creates/uses it, not a worker).
#
# NOTE (per the slide): if the workflow is straightforward and not
# actually agentic - e.g. a fixed pipeline like 13_2's - a
# hierarchical crew is unnecessary overhead. It earns its keep here
# because the manager genuinely doesn't know in advance how many
# specialists it needs to consult, or in what order, to answer an
# open-ended "should we buy this stock?" question.
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
        f"Trailing P/E: {info.get('trailingPE', 'n/a')} | Forward P/E: {info.get('forwardPE', 'n/a')}\n"
        f"Revenue growth (YoY): {info.get('revenueGrowth', 'n/a')}\n"
        f"Profit margin: {info.get('profitMargins', 'n/a')}\n"
        f"Debt to equity: {info.get('debtToEquity', 'n/a')}\n"
        f"52-week range: {info.get('fiftyTwoWeekLow', 'n/a')} - {info.get('fiftyTwoWeekHigh', 'n/a')}"
    )


@tool("RecentNews")
def get_recent_news(ticker: str) -> str:
    """Fetch recent real news headlines for a stock ticker from Yahoo Finance."""
    items = yf.Ticker(ticker).news or []
    titles = [item.get("content", {}).get("title") for item in items[:5]]
    titles = [t for t in titles if t]
    if not titles:
        return f"No recent news found for '{ticker}'."
    return "\n".join(f"- {t}" for t in titles)


fundamentals_analyst = Agent(
    role="Fundamentals Analyst",
    goal="Assess a company's financial health from its live fundamentals",
    backstory="You judge profitability, growth and leverage from raw financial metrics.",
    tools=[get_stock_snapshot],
    llm="gpt-4o-mini",
    verbose=True,
)

news_analyst = Agent(
    role="News & Sentiment Analyst",
    goal="Assess how recent news might affect a stock's near-term outlook",
    backstory="You read real recent headlines and judge sentiment, without inventing events.",
    tools=[get_recent_news],
    llm="gpt-4o-mini",
    verbose=True,
)

valuation_analyst = Agent(
    role="Valuation Analyst",
    goal="Judge whether a stock looks cheap, fair, or expensive relative to its fundamentals",
    backstory="You reason about P/E ratios and analyst targets relative to growth and margins.",
    tools=[get_stock_snapshot],
    llm="gpt-4o-mini",
    verbose=True,
)

research_manager = Agent(
    role="Research Manager",
    goal="Coordinate specialist analysts to produce one final investment recommendation",
    backstory=(
        "You understand the overall research objective, delegate specific sub-questions "
        "to the right specialist analyst, review their findings, decide if anything needs "
        "more work, and coordinate everything into one final recommendation. You never do "
        "the specialist research yourself - you only delegate, review, and synthesize."
        " Try for a maximimum of 5 steps/iterations."
    ),
    llm="gpt-4o-mini",
    verbose=True,
)

# In a hierarchical Crew the task has no `agent=` - the manager decides
# at runtime which specialist(s) to delegate each part of it to.
recommendation_task = Task(
    description=(
        "Produce a final buy/hold/sell recommendation for {ticker}. Delegate to the "
        "Fundamentals Analyst, News & Sentiment Analyst, and Valuation Analyst as needed, "
        "review what each comes back with, and decide if any of them need to dig deeper "
        "before you finalize your recommendation."
    ),
    expected_output=(
        "A final buy/hold/sell recommendation for {ticker}, with one supporting "
        "reason drawn from fundamentals, one from recent news, and one from valuation."
    ),
)

crew = Crew(
    agents=[fundamentals_analyst, news_analyst, valuation_analyst],  # workers only - the manager is separate
    tasks=[recommendation_task],
    process=Process.hierarchical,
    manager_agent=research_manager,
    verbose=True,
)

if __name__ == "__main__":
    result = crew.kickoff(inputs={"ticker": "MSFT"})
    print("\n" + "=" * 70)
    print("FINAL RECOMMENDATION")
    print("=" * 70)
    print(result)
