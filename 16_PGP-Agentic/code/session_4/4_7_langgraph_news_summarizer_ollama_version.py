# pip install langchain-ollama langchain-core langgraph python-dotenv requests

from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage
from dotenv import load_dotenv
import os, requests
from langgraph.graph import StateGraph, END
from typing import TypedDict

# --------------------------
# Shared State
# --------------------------
class AgentState(TypedDict):
    topic: str
    headlines: str
    summary: str
    sentiment: str
    final_report: str
    sentiment_label: str

# --------------------------
# Setup
# --------------------------
load_dotenv(override=True)

# Use local Ollama model
llm = ChatOllama(
    model="llama3.2",     
    temperature=0.3
)

news_key = os.getenv("NEWS_API_KEY")

# --------------------------
# Agent Functions
# --------------------------
def fetch_news(state: AgentState) -> AgentState:
    print("Agent 1: Fetching news...")
    url = f"https://newsapi.org/v2/everything?q={state['topic']}&apiKey={news_key}&pageSize=5"
    try:
        r = requests.get(url)
        articles = [a["title"] for a in r.json().get("articles", [])]
        headlines = "\n".join(articles)
        print(f"Headlines: {headlines}") # For debugging
    except Exception as e:
        headlines = f"Error fetching news: {e}"
    return {"headlines": headlines}

def summarize_news(state: AgentState) -> AgentState:
    print("Agent 2: Summarizing news...")
    prompt = f"Summarize these headlines about {state['topic']}:\n{state['headlines']}"
    resp = llm.invoke([HumanMessage(content=prompt)])
    return {"summary": resp.content}

def analyze_sentiment(state: AgentState) -> AgentState:
    print("Agent 3: Analyzing sentiment...")
    prompt = f"Is this summary overall positive or negative?\n\n{state['summary']}"
    resp = llm.invoke([HumanMessage(content=prompt)])
    sentiment = resp.content.strip().lower()
    label = "positive" if "positive" in sentiment else "negative"
    print(f"Sentiment: {sentiment} ({label})")
    return {"sentiment": sentiment, "sentiment_label": label}

def investor_summary(state: AgentState) -> AgentState:
    print("Agent 4A: Creating investor summary...")
    prompt = f"Write an investor-focused insight based on:\n{state['summary']}"
    resp = llm.invoke([HumanMessage(content=prompt)])
    return {"final_report": resp.content}

def public_summary(state: AgentState) -> AgentState:
    print("Agent 4B: Creating public summary...")
    prompt = f"Write a short public news digest based on:\n{state['summary']}"
    resp = llm.invoke([HumanMessage(content=prompt)])
    return {"final_report": resp.content}

# --------------------------
# Build Graph
# --------------------------
workflow = StateGraph(AgentState)

workflow.add_node("fetch_news", fetch_news)
workflow.add_node("summarize_news", summarize_news)
workflow.add_node("analyze_sentiment", analyze_sentiment)
workflow.add_node("investor_summary", investor_summary)
workflow.add_node("public_summary", public_summary)

workflow.set_entry_point("fetch_news")
workflow.add_edge("fetch_news", "summarize_news")
workflow.add_edge("summarize_news", "analyze_sentiment")

workflow.add_conditional_edges(
    "analyze_sentiment",
    lambda state: "investor_summary" if state["sentiment_label"] == "positive" else "public_summary"
)

workflow.add_edge("investor_summary", END)
workflow.add_edge("public_summary", END)

app = workflow.compile()

# --------------------------
# Run in a loop for multiple topics
# --------------------------
if __name__ == "__main__":
    print("Enter a topic to fetch news and summaries. Type 'exit' to quit.")
    while True:
        topic = input("\nEnter topic: ").strip()
        if topic.lower() == "exit":
            print("Exiting...")
            break

        initial = {
            "topic": topic,
            "headlines": "",
            "summary": "",
            "sentiment": "",
            "final_report": "",
            "sentiment_label": ""
        }

        result = app.invoke(initial)
        print("\n" + "=" * 60)
        print(f"Topic: {topic}")
        print(result["final_report"])
        print("=" * 60)
