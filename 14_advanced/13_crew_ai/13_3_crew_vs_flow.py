import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

import sys
import yfinance as yf
from dotenv import load_dotenv
from pydantic import BaseModel
from crewai import Agent, Task, Crew
from crewai.flow.flow import Flow, start, listen, router, or_

load_dotenv(override=True)
sys.stdout.reconfigure(encoding="utf-8")

# =====================================================================
# Crew vs Flow: a Crew is a team of agents collaborating on tasks - it
# answers "who does the work?". A Flow is the control layer around it
# - it answers "how does the application run?": what happens next,
# which path to take, and what state carries forward between steps.
#
# This Flow fetches a live stock snapshot, DECIDES (via @router)
# whether the data is good enough to analyze, and only on the "good"
# path hands the work to a real Crew - Flow orchestrates, Crew
# executes. Building blocks used: @start, @router, @listen, or_(),
# and a shared Pydantic state object carried across every step.
# =====================================================================


class ResearchState(BaseModel):
    ticker: str = "AAPL"
    snapshot: str = ""
    confidence: float = 0.0
    report: str = ""


class StockResearchFlow(Flow[ResearchState]):

    @start()
    def fetch_snapshot(self):
        info = yf.Ticker(self.state.ticker).info
        fields = ["shortName", "currentPrice", "trailingPE", "revenueGrowth", "profitMargins", "recommendationKey"]
        present = [f for f in fields if info.get(f) is not None]
        self.state.confidence = len(present) / len(fields)
        self.state.snapshot = (
            f"{info.get('shortName', self.state.ticker)}: "
            f"price={info.get('currentPrice', 'n/a')}, "
            f"P/E={info.get('trailingPE', 'n/a')}, "
            f"revenue growth={info.get('revenueGrowth', 'n/a')}, "
            f"margin={info.get('profitMargins', 'n/a')}, "
            f"recommendation={info.get('recommendationKey', 'n/a')}"
        )
        print(f"[fetch_snapshot] confidence={self.state.confidence:.2f}")

    @router(fetch_snapshot)
    def route_on_confidence(self):
        # Same pattern as: if result.confidence > 0.8: return "good" else "retry"
        if self.state.confidence >= 0.8:
            return "good"
        return "retry"

    @listen("retry")
    def handle_low_confidence(self):
        self.state.report = (
            f"Not enough live data was available for '{self.state.ticker}' "
            f"(confidence={self.state.confidence:.2f}) - skipping full analysis."
        )
        print("[handle_low_confidence]", self.state.report)

    @listen("good")
    def analyze_with_crew(self):
        # This is the "who does the work" half - a real Crew, invoked
        # FROM the Flow, only on the path the Flow decided was worth it.
        equity_analyst = Agent(
            role="Equity Analyst",
            goal="Turn a raw stock snapshot into a short investment take",
            backstory="You give balanced, evidence-based takes grounded only in the data given.",
            llm="gpt-4o-mini",
        )
        analysis_task = Task(
            description=f"Given this snapshot, write a 2-3 sentence investment take:\n{self.state.snapshot}",
            expected_output="A short, balanced investment take grounded in the snapshot",
            agent=equity_analyst,
        )
        crew = Crew(agents=[equity_analyst], tasks=[analysis_task])
        result = crew.kickoff()
        self.state.report = str(result)
        print("[analyze_with_crew]", self.state.report)

    @listen(or_(handle_low_confidence, analyze_with_crew))
    def finalize_report(self):
        # Both routes converge here - the Flow's shared state carries
        # forward whatever each branch wrote into self.state.report.
        print("\n[finalize_report] final report pulled from Flow state:")
        print(self.state.report)
        return self.state.report


if __name__ == "__main__":
    print("=" * 70)
    print("RUN 1: a real ticker - should route to 'good' -> analyze_with_crew")
    print("=" * 70)
    good_flow = StockResearchFlow()
    good_flow.kickoff(inputs={"ticker": "AAPL"})

    print("\n" + "=" * 70)
    print("RUN 2: an invalid ticker - should route to 'retry' -> handle_low_confidence")
    print("=" * 70)
    retry_flow = StockResearchFlow()
    retry_flow.kickoff(inputs={"ticker": "NOT_A_REAL_TICKER_XYZ"})
