import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

import os
import sys
from typing import Literal, TypedDict
from dotenv import load_dotenv
from pydantic import BaseModel, Field
import yfinance as yf
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, START, END

load_dotenv(override=True)

# LLM/yfinance output can contain characters outside Windows' default
# console codepage (cp1252) - reconfigure stdout to UTF-8 so printing
# doesn't crash.
sys.stdout.reconfigure(encoding="utf-8")

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)

# =====================================================================
# Same idea as stock_price_graph.py's plain node chain, plus a branch:
# fetch_news -> classify_sentiment -> conditional edge -> one of two
# summary nodes, depending on the sentiment the LLM assigns to the
# news. add_conditional_edges picks the next node at runtime instead
# of the fixed add_edge used everywhere else in this graph.
# =====================================================================


class StockNewsState(TypedDict):
    stock_name: str
    news_summary: str
    sentiment: str
    result: str


class SentimentClassification(BaseModel):
    sentiment: Literal["positive", "negative"] = Field(
        description="Overall investment sentiment of the news."
    )


sentiment_prompt = ChatPromptTemplate.from_template(
    "Classify the overall investment sentiment of this news about {stock_name} "
    "as positive or negative:\n\n{news_summary}"
)
sentiment_chain = sentiment_prompt | llm.with_structured_output(SentimentClassification)


def normalize_symbol(state: StockNewsState) -> StockNewsState:
    return {"stock_name": state["stock_name"].strip().upper()}


def fetch_news(state: StockNewsState) -> StockNewsState:
    symbol = state["stock_name"]
    # NSE-listed Indian stocks need a ".NS" suffix on Yahoo Finance
    # ("TCS" -> "TCS.NS").
    candidate = f"{symbol}.NS"
    try:
        articles = yf.Ticker(candidate).news[:5]
    except Exception:
        articles = []
    if articles:
        lines = [
            f"- {a['content']['title']}: {a['content']['summary']}"
            for a in articles
            if a.get("content", {}).get("title")
        ]
        return {"stock_name": candidate, "news_summary": "\n".join(lines) or "No recent news found."}
    return {"stock_name": candidate, "news_summary": "No recent news found."}


def classify_sentiment(state: StockNewsState) -> StockNewsState:
    result = sentiment_chain.invoke({
        "stock_name": state["stock_name"],
        "news_summary": state["news_summary"],
    })
    return {"sentiment": result.sentiment}


def route_by_sentiment(state: StockNewsState) -> str:
    return state["sentiment"]


def invest_summary(state: StockNewsState) -> StockNewsState:
    response = llm.invoke(
        f"Based on this recent news about {state['stock_name']}, write a short "
        "2-3 sentence summary of why an investor might consider buying it:\n\n"
        f"{state['news_summary']}"
    )
    return {"result": response.content}


def alternatives_summary(state: StockNewsState) -> StockNewsState:
    response = llm.invoke(
        f"Based on this recent negative news about {state['stock_name']}, write "
        "a short 2-3 sentence summary suggesting what kind of alternative "
        "stocks or sectors an investor might consider instead:\n\n"
        f"{state['news_summary']}"
    )
    return {"result": response.content}


graph = StateGraph(StockNewsState)
graph.add_node("normalize_symbol", normalize_symbol)
graph.add_node("fetch_news", fetch_news)
graph.add_node("classify_sentiment", classify_sentiment)
graph.add_node("invest_summary", invest_summary)
graph.add_node("alternatives_summary", alternatives_summary)

graph.add_edge(START, "normalize_symbol")
graph.add_edge("normalize_symbol", "fetch_news")
graph.add_edge("fetch_news", "classify_sentiment")
graph.add_conditional_edges(
    "classify_sentiment",
    route_by_sentiment,
    {"positive": "invest_summary", "negative": "alternatives_summary"},
)
graph.add_edge("invest_summary", END)
graph.add_edge("alternatives_summary", END)

app = graph.compile()

# --------------------------
# Draw and save graph image (best-effort - needs internet access since
# draw_mermaid_png renders via the remote mermaid.ink API).
# --------------------------
try:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    graph_path = os.path.join(BASE_DIR, "stock_news_sentiment_graph.png")
    app.get_graph().draw_mermaid_png(output_file_path=graph_path)
    print(f"Graph image saved at: {graph_path}")
except Exception as exc:
    print(f"(skipped graph image - {exc})")

if __name__ == "__main__":
    stock_name = input("Enter a stock symbol (e.g. TCS): ").strip() or "TCS"
    result = app.invoke({
        "stock_name": stock_name,
        "news_summary": "",
        "sentiment": "",
        "result": "",
    })
    print(f"\nSentiment: {result['sentiment']}")
    print(f"\n{result['result']}")
