import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

import os
import sys
from typing import TypedDict
import yfinance as yf
from langgraph.graph import StateGraph, START, END

# yfinance output can contain characters outside Windows' default console
# codepage (cp1252) - reconfigure stdout to UTF-8 so printing doesn't crash.
sys.stdout.reconfigure(encoding="utf-8")

# =====================================================================
# The simplest possible LangGraph: three nodes chained by plain,
# unconditional edges (graph.add_edge - no add_conditional_edges, no
# branching, no LLM). State is just a dict that flows through the
# graph; each node reads what it needs from it and returns the piece
# it's responsible for filling in.
# =====================================================================


class StockState(TypedDict):
    stock_name: str
    price: str


def normalize_symbol(state: StockState) -> StockState:
    return {"stock_name": state["stock_name"].strip().upper()}


def fetch_price(state: StockState) -> StockState:
    symbol = state["stock_name"]
    # NSE-listed Indian stocks need a ".NS" suffix on Yahoo Finance
    # ("TCS" -> "TCS.NS"). yfinance also raises inconsistent,
    # undocumented exception types for an invalid/delisted symbol -
    # catch broadly so a bad symbol prints a message instead of a
    # crash-ending traceback.
    #candidate = f"{symbol}.NS"
    candidate = f"{symbol}"
    try:
        last_price = yf.Ticker(candidate).fast_info["lastPrice"]
        return {"stock_name": candidate, "price": f"{last_price:.2f}"}
    except Exception:
        return {"stock_name": candidate, "price": "not found (checked with the NSE .NS suffix)"}


def show_result(state: StockState) -> StockState:
    print(f"{state['stock_name']}: {state['price']}")
    return {}


graph = StateGraph(StockState)
graph.add_node("normalize_symbol", normalize_symbol)
graph.add_node("fetch_price", fetch_price)
graph.add_node("show_result", show_result)

graph.add_edge(START, "normalize_symbol")
graph.add_edge("normalize_symbol", "fetch_price")
graph.add_edge("fetch_price", "show_result")
graph.add_edge("show_result", END)

app = graph.compile()

# --------------------------
# Draw and save graph image (best-effort - needs internet access since
# draw_mermaid_png renders via the remote mermaid.ink API).
# --------------------------
try:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    graph_path = os.path.join(BASE_DIR, "stock_price_graph.png")
    app.get_graph().draw_mermaid_png(output_file_path=graph_path)
    print(f"Graph image saved at: {graph_path}")
except Exception as exc:
    print(f"(skipped graph image - {exc})")

if __name__ == "__main__":
    stock_name = input("Enter a stock symbol (e.g. TCS): ").strip() or "TCS"
    app.invoke({"stock_name": stock_name, "price": ""})
