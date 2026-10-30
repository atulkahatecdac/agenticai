import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

import sys
from typing import TypedDict
from dotenv import load_dotenv
import pandas as pd
import yfinance as yf
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END

load_dotenv(override=True)

# Tool/LLM output can contain characters outside Windows' default console
# codepage (cp1252) - reconfigure stdout to UTF-8 so printing doesn't crash.
sys.stdout.reconfigure(encoding="utf-8")

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3, streaming=True)


class StockState(TypedDict):
    ticker: str
    returns_summary: str
    financials_summary: str
    recommendation: str


# ---------------------------------------------------------------------
# Node 1: historical returns from Yahoo Finance price history.
# ---------------------------------------------------------------------
def _pct_return(hist: pd.DataFrame, years: int):
    if hist.empty:
        return None
    target_date = hist.index[-1] - pd.DateOffset(years=years)
    past = hist[hist.index <= target_date]
    if past.empty:
        return None
    start_price = float(past["Close"].iloc[-1])
    end_price = float(hist["Close"].iloc[-1])
    return (end_price - start_price) / start_price * 100


def fetch_stock_returns(state: StockState) -> StockState:
    print(f"[fetch_stock_returns] downloading price history for {state['ticker']}...")
    # yfinance's period="5y" starts exactly one calendar day short of a
    # full 5 years back (weekend/holiday alignment), which makes the
    # 5-year return calculation below miss its target date by one row.
    # Asking for "10y" instead gives enough buffer to always cover a
    # full 5-year lookback.
    hist = yf.Ticker(state["ticker"]).history(period="10y", interval="1d")

    lines = []
    for years in (1, 3, 5):
        r = _pct_return(hist, years)
        if r is not None:
            lines.append(f"{years}-year return: {r:.1f}%")
        else:
            lines.append(f"{years}-year return: not available (insufficient price history)")

    return {"returns_summary": "\n".join(lines)}


# ---------------------------------------------------------------------
# Node 2: latest financial results - a mix of trailing-twelve-month
# ratios from .info and the actual most recent quarter's Total Revenue
# / Net Income from .quarterly_financials.
# ---------------------------------------------------------------------
def fetch_financial_results(state: StockState) -> StockState:
    print(f"[fetch_financial_results] pulling latest financials for {state['ticker']}...")
    ticker = yf.Ticker(state["ticker"])
    info = ticker.info

    lines = [
        f"Company: {info.get('longName') or state['ticker']}",
        f"Trailing 12-month revenue: {info.get('totalRevenue', 'N/A')}",
        f"Revenue growth (YoY): {info.get('revenueGrowth', 'N/A')}",
        f"Earnings growth (YoY): {info.get('earningsGrowth', 'N/A')}",
        f"Trailing P/E: {info.get('trailingPE', 'N/A')}",
        f"Profit margin: {info.get('profitMargins', 'N/A')}",
    ]

    try:
        quarterly = ticker.quarterly_financials
        latest_col = quarterly.columns[0]
        if "Total Revenue" in quarterly.index:
            lines.append(
                f"Most recent quarter ({latest_col.date()}) Total Revenue: "
                f"{quarterly.loc['Total Revenue', latest_col]:,.0f}"
            )
        if "Net Income" in quarterly.index:
            lines.append(
                f"Most recent quarter ({latest_col.date()}) Net Income: "
                f"{quarterly.loc['Net Income', latest_col]:,.0f}"
            )
    except Exception as e:
        lines.append(f"(quarterly financials unavailable: {e})")

    return {"financials_summary": "\n".join(lines)}


# ---------------------------------------------------------------------
# Node 3: buy/sell/hold recommendation, streamed from the LLM.
# ---------------------------------------------------------------------
def generate_recommendation(state: StockState) -> StockState:
    prompt = f"""You are an investment analyst. Based on the data below for {state['ticker']}, \
give a clear recommendation: BUY, SELL, or HOLD, followed by a short 2-3 sentence rationale.

Historical returns:
{state['returns_summary']}

Latest financial results:
{state['financials_summary']}
"""
    response = llm.invoke([HumanMessage(content=prompt)])
    return {"recommendation": response.content}


# ---------------------------------------------------------------------
# Graph: START -> fetch_stock_returns -> fetch_financial_results ->
# generate_recommendation -> END
# ---------------------------------------------------------------------
graph = StateGraph(StockState)
graph.add_node("fetch_stock_returns", fetch_stock_returns)
graph.add_node("fetch_financial_results", fetch_financial_results)
graph.add_node("generate_recommendation", generate_recommendation)

graph.add_edge(START, "fetch_stock_returns")
graph.add_edge("fetch_stock_returns", "fetch_financial_results")
graph.add_edge("fetch_financial_results", "generate_recommendation")
graph.add_edge("generate_recommendation", END)

app = graph.compile()

if __name__ == "__main__":
    ticker = "AAPL"
    initial = {
        "ticker": ticker,
        "returns_summary": "",
        "financials_summary": "",
        "recommendation": "",
    }

    # -------------------------------------------------------------
    # 1. NODE-LEVEL streaming - stream_mode="updates" yields one chunk
    # per node, as soon as that node finishes, containing only that
    # node's partial state update. Good for a progress indicator
    # ("fetching returns... done, fetching financials... done, ...")
    # without waiting for the whole graph to finish.
    # -------------------------------------------------------------
    print("=" * 70)
    print("1. NODE-LEVEL streaming (stream_mode='updates')")
    print("=" * 70)

    for update in app.stream(initial, stream_mode="updates"):
        for node_name, partial_state in update.items():
            print(f"--- node '{node_name}' finished ---")
            for key, value in partial_state.items():
                print(f"{key}:\n{value}\n")

    # -------------------------------------------------------------
    # 2. TOKEN-LEVEL streaming - stream_mode="messages" yields
    # (message_chunk, metadata) tuples for every token any chat model
    # emits inside any node, live, as it's generated - regardless of
    # which node calls the LLM. Filtering on
    # metadata["langgraph_node"] shows only the recommendation node's
    # tokens as they arrive, the way a chat UI renders a reply live.
    # Re-running the whole graph here (yfinance calls repeat) purely
    # to keep this file's two sections independent and easy to read
    # top to bottom; a real app would fetch the data once and stream
    # only the final generation step.
    # -------------------------------------------------------------
    print("=" * 70)
    print("2. TOKEN-LEVEL streaming (stream_mode='messages')")
    print("=" * 70)
    print(f"\nStreaming recommendation for {ticker} live:\n")

    for message_chunk, metadata in app.stream(initial, stream_mode="messages"):
        if metadata.get("langgraph_node") == "generate_recommendation":
            print(message_chunk.content, end="", flush=True)
    print("\n")
