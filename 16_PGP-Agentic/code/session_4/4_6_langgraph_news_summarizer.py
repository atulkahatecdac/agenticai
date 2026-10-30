# pip install langchain-openai langchain-core langgraph python-dotenv requests

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from dotenv import load_dotenv
import os, requests
from langgraph.graph import StateGraph, START, END
from typing import TypedDict

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

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

llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.3
)

news_key = os.getenv("NEWS_API_KEY")


# --------------------------
# Agent Functions
# --------------------------
def fetch_news(state: AgentState) -> AgentState:
    print("Agent 1: Fetching news...")

    url = (
        f"https://newsapi.org/v2/everything?"
        f"q={state['topic']}"
        f"&apiKey={news_key}"
        f"&pageSize=5"
    )

    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()

        articles = [a["title"] for a in r.json().get("articles", [])]
        headlines = "\n".join(articles)

    except Exception as e:
        headlines = f"Error fetching news: {e}"

    return {"headlines": headlines}


def summarize_news(state: AgentState) -> AgentState:
    print("Agent 2: Summarizing news...")

    prompt = f"""
Summarize these headlines about {state['topic']}:

{state['headlines']}
"""

    resp = llm.invoke([HumanMessage(content=prompt)])

    return {"summary": resp.content}


def analyze_sentiment(state: AgentState) -> AgentState:
    print("Agent 3: Analyzing sentiment...")

    prompt = f"""
Return ONLY one word.

positive

or

negative

Summary:

{state['summary']}
"""

    resp = llm.invoke([HumanMessage(content=prompt)])

    label = resp.content.strip().lower()

    if label not in ["positive", "negative"]:
        label = "negative"

    print(f"Sentiment: {label}")

    return {
        "sentiment": label,
        "sentiment_label": label
    }


def investor_summary(state: AgentState) -> AgentState:
    print("Agent 4A: Creating investor summary...")

    prompt = f"""
Write an investor-focused insight based on:

{state['summary']}
"""

    resp = llm.invoke([HumanMessage(content=prompt)])

    return {"final_report": resp.content}


def public_summary(state: AgentState) -> AgentState:
    print("Agent 4B: Creating public summary...")

    prompt = f"""
Write a short public news digest based on:

{state['summary']}
"""

    resp = llm.invoke([HumanMessage(content=prompt)])

    return {"final_report": resp.content}


# --------------------------
# Routing Function
# --------------------------
def route(state: AgentState):
    if state["sentiment_label"] == "positive":
        return "investor_summary"

    return "public_summary"


# --------------------------
# Build Graph
# --------------------------
workflow = StateGraph(AgentState)

workflow.add_node("fetch_news", fetch_news)
workflow.add_node("summarize_news", summarize_news)
workflow.add_node("analyze_sentiment", analyze_sentiment)
workflow.add_node("investor_summary", investor_summary)
workflow.add_node("public_summary", public_summary)

workflow.add_edge(START, "fetch_news")

workflow.add_edge("fetch_news", "summarize_news")
workflow.add_edge("summarize_news", "analyze_sentiment")

workflow.add_conditional_edges(
    "analyze_sentiment",
    route
)

workflow.add_edge("investor_summary", END)
workflow.add_edge("public_summary", END)

app = workflow.compile()


# --------------------------
# Draw and save graph image
# --------------------------
print("Generating graph image...")

graph = app.get_graph()

graph_path = os.path.join(BASE_DIR, "news_agent_graph.png")

graph.draw_mermaid_png(output_file_path=graph_path)

print(f"Graph image saved at: {graph_path}")


# --------------------------
# Run
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