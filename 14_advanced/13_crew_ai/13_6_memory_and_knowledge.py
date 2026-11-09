import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

import os
import sys
from pathlib import Path
import yfinance as yf
from dotenv import load_dotenv
from crewai import Agent, Task, Crew
from crewai.tools import tool
from crewai.knowledge.source.string_knowledge_source import StringKnowledgeSource
from crewai.knowledge.source.pdf_knowledge_source import PDFKnowledgeSource

load_dotenv(override=True)
sys.stdout.reconfigure(encoding="utf-8")

# =====================================================================
# Memory vs Knowledge (they answer different questions):
#   - Knowledge: "What information do I need to know?" - static
#     reference material an agent can look things up in. Two sources
#     here: a hand-written glossary (StringKnowledgeSource) and a real
#     one-page PDF reference, Buffett_Munger_Top_10_Investment_Ratios.pdf
#     (PDFKnowledgeSource) - a genuine "Buffett & Munger-style" ratio
#     checklist (ROE, ROIC, debt-to-equity, etc.) with what each ratio
#     means and what to look for. A knowledge_sources list can combine
#     several real documents like this, not just one.
#   - Memory: "What do I remember from previous interactions?" -
#     carried across separate crew.kickoff() calls when memory=True.
#     Here it's the user's stated risk tolerance from an earlier
#     kickoff, applied automatically on a LATER, unrelated kickoff
#     that never restates it.
# Flow State (see 13_3) is neither of these - it's temporary context
# for ONE run, gone once that Flow finishes.
#
# Contrast with 14_advanced/12_deep_agents/: those scripts hand-roll a
# persistent Chroma store to get this same behavior explicitly. Here
# memory=True and knowledge_sources=[...] get it from CrewAI itself.
# =====================================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

INVESTING_GLOSSARY = """
P/E ratio (price-to-earnings): share price divided by earnings per share; a
rough measure of how expensive a stock is relative to its profits.
Market cap: share price multiplied by total shares outstanding; the total
market value of the company.
Dividend yield: annual dividend per share divided by share price; how much
cash income a stock pays relative to its price.
Beta: a stock's volatility relative to the overall market; beta above 1
means it tends to swing more than the market, below 1 means less.
"""

glossary_knowledge = StringKnowledgeSource(content=INVESTING_GLOSSARY)

# A Path (not a plain string) is passed here so CrewAI uses it as-is
# instead of resolving it against its default "knowledge/" subfolder.
buffett_munger_ratios = PDFKnowledgeSource(
    file_paths=[Path(BASE_DIR) / "Buffett_Munger_Top_10_Investment_Ratios.pdf"]
)


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
        f"Dividend yield: {info.get('dividendYield', 'n/a')}\n"
        f"Beta: {info.get('beta', 'n/a')}\n"
        f"Return on equity (ROE): {info.get('returnOnEquity', 'n/a')}\n"
        f"Debt to equity: {info.get('debtToEquity', 'n/a')}"
    )


advisor = Agent(
    role="Portfolio Advisor",
    goal="Explain a stock's metrics in plain English, tailored to the investor's known risk tolerance",
    backstory=(
        "You use the investing glossary to explain jargon, the Buffett & Munger-style "
        "ratio checklist to judge whether a company's numbers look strong, and you "
        "remember what this investor has told you before."
    ),
    tools=[get_stock_snapshot],
    knowledge_sources=[glossary_knowledge, buffett_munger_ratios],
    llm="gpt-4o-mini",
    verbose=True,
)

crew = Crew(
    agents=[advisor],
    tasks=[],  # tasks are built per-kickoff below, agent + memory persist across them
    memory=True,
    verbose=True,
)


def ask(query: str) -> str:
    # crew.kickoff() re-runs agent.set_knowledge() -> source.add() on every
    # call, and add() does self.chunks.extend(...) instead of replacing.
    # Since these are the same source objects across kickoffs, chunks would
    # otherwise double up on kickoff 2+ and hit chromadb's DuplicateIDError
    # (content-hash IDs repeated within the same upsert). Clear them first
    # so each kickoff re-adds exactly one copy.
    for source in advisor.knowledge_sources:
        source.chunks = []
        source.chunk_embeddings = []

    task = Task(
        description=query,
        expected_output="A plain-English answer, using the glossary for any jargon, respecting known risk tolerance",
        agent=advisor,
    )
    crew.tasks = [task]
    return str(crew.kickoff())


if __name__ == "__main__":
    crew.reset_memories("all")  # start clean so this demo is repeatable

    print("=" * 70)
    print("KICKOFF 1: investor states their risk tolerance")
    print("=" * 70)
    answer1 = ask(
        "I'm a conservative investor who cares most about dividend stability, not growth. "
        "What's the dividend yield on KO (Coca-Cola) and is that a reasonable holding for me?"
    )
    print(answer1)

    print("\n" + "=" * 70)
    print("KICKOFF 2: different ticker, risk tolerance NEVER restated -")
    print("should still be applied from memory of kickoff 1, and now also")
    print("draws on the Buffett & Munger ratio checklist (PDF knowledge)")
    print("=" * 70)
    answer2 = ask(
        "Using the Buffett & Munger-style ratio checklist, how does TSLA's ROE and "
        "debt-to-equity look, and is this a good fit given what I told you about my portfolio?"
    )
    print(answer2)
