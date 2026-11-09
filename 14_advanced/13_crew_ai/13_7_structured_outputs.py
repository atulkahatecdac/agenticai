import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

import sys
import yfinance as yf
from dotenv import load_dotenv
from pydantic import BaseModel
from crewai import Agent, Task, Crew
from crewai.tools import tool

load_dotenv(override=True)
sys.stdout.reconfigure(encoding="utf-8")

# =====================================================================
# Structured outputs and reliable agent communication: a Task with
# output_pydantic=<Model> forces the agent's final answer to validate
# against a real schema - the receiving code gets typed Python fields
# (finding.confidence, finding.risk_level, ...), not a string to
# re-parse. That means downstream code can make real branching
# decisions (not just prompt text) based on what the first agent found.
# =====================================================================


class ResearchFinding(BaseModel):
    company: str
    revenue_growth: float  # decimal fraction, e.g. 0.12 for 12%
    risk_level: str        # "low" | "medium" | "high"
    confidence: float      # 0-1
    evidence: list[str]


@tool("StockSnapshot")
def get_stock_snapshot(ticker: str) -> str:
    """Fetch a live snapshot of key financial metrics for a stock ticker from Yahoo Finance."""
    info = yf.Ticker(ticker).info
    if not info or info.get("shortName") is None:
        return f"No data found for ticker '{ticker}'."
    return (
        f"{info.get('shortName')} ({ticker.upper()})\n"
        f"Revenue growth (YoY): {info.get('revenueGrowth', 'n/a')}\n"
        f"Profit margin: {info.get('profitMargins', 'n/a')}\n"
        f"Debt to equity: {info.get('debtToEquity', 'n/a')}\n"
        f"Beta: {info.get('beta', 'n/a')}"
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


researcher = Agent(
    role="Equity Researcher",
    goal="Produce a structured, evidence-backed research finding for a stock",
    backstory="You back every field with real data or headlines pulled from your tools - never invent numbers.",
    tools=[get_stock_snapshot, get_recent_news],
    llm="gpt-4o-mini",
    verbose=True,
)

research_task = Task(
    description=(
        "Research {ticker} using the StockSnapshot and RecentNews tools. Report "
        "revenue_growth as a decimal fraction (e.g. 0.12 for 12%), assess risk_level "
        "as low/medium/high based on debt and margins, give your confidence (0-1) in "
        "this assessment, and list the specific data points/headlines you used as evidence."
    ),
    expected_output="A structured ResearchFinding",
    agent=researcher,
    output_pydantic=ResearchFinding,
)

research_crew = Crew(agents=[researcher], tasks=[research_task], verbose=True)

writer = Agent(
    role="Investor Note Writer",
    goal="Turn a validated research finding into a short investor note",
    backstory="You trust the structured fields you're handed and don't re-derive or second-guess them.",
    llm="gpt-4o-mini",
    verbose=True,
)

if __name__ == "__main__":
    research_crew.kickoff(inputs={"ticker": "NVDA"})
    finding: ResearchFinding = research_task.output.pydantic

    print("=" * 70)
    print("VALIDATED STRUCTURED FINDING (typed Python object, not a string)")
    print("=" * 70)
    print(finding.model_dump_json(indent=2))

    # Reliable agent communication: because these fields are validated
    # and typed, plain Python can branch on them directly - no prompt
    # re-parsing needed to decide this.
    caution_note = "" if finding.confidence >= 0.6 else (
        "IMPORTANT: confidence is low - explicitly flag that more research is needed.\n"
    )

    writer_task = Task(
        description=(
            f"{caution_note}"
            f"Write a short investor note for {finding.company}. "
            f"Revenue growth: {finding.revenue_growth:.1%}. Risk level: {finding.risk_level}. "
            f"Confidence: {finding.confidence:.0%}. Evidence: {'; '.join(finding.evidence)}."
        ),
        expected_output="A short investor note in plain English",
        agent=writer,
    )
    writer_crew = Crew(agents=[writer], tasks=[writer_task], verbose=True)
    result = writer_crew.kickoff()

    print("\n" + "=" * 70)
    print("INVESTOR NOTE")
    print("=" * 70)
    print(result)
