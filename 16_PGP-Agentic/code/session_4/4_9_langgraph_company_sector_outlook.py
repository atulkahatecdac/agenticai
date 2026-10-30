import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from dotenv import load_dotenv
import yfinance as yf
from langgraph.graph import StateGraph, END
from typing import TypedDict

# --------------------------
# Shared State
# --------------------------
class AgentState(TypedDict):
    ticker: str
    company_data: str
    summary: str
    outlook: str
    outlook_label: str
    final_report: str

# --------------------------
# Setup
# --------------------------
load_dotenv(override=True)

# Use OpenAI model
llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.3,
)

def get_text(resp):
    return resp.content

# --------------------------
# Agent Functions
# --------------------------
def fetch_company_data(state: AgentState) -> AgentState:
    print("Agent 1: Fetching company/sector data from Yahoo Finance...")

    try:
        ticker = yf.Ticker(state["ticker"])
        info = ticker.info

        name = info.get("longName") or info.get("shortName") or state["ticker"]
        sector = info.get("sector", "Unknown sector")
        industry = info.get("industry", "Unknown industry")
        business_summary = info.get("longBusinessSummary", "")

        news_items = ticker.news or []
        headlines = [
            item.get("content", {}).get("title") or item.get("title")
            for item in news_items[:5]
        ]
        headlines = [h for h in headlines if h]

        lines = [
            f"Company: {name}",
            f"Sector: {sector}",
            f"Industry: {industry}",
            f"Business summary: {business_summary[:500]}",
            "Recent headlines:",
        ] + [f"- {h}" for h in headlines]

        company_data = "\n".join(lines)
        print(f"Company data:\n{company_data}")
    except Exception as e:
        company_data = f"Error fetching data from Yahoo Finance: {e}"

    return {"company_data": company_data}

def fetch_failed(state: AgentState) -> AgentState:
    print("Company data unavailable, skipping analysis.")
    return {"final_report": f"Could not analyze the outlook: {state['company_data']}"}

def summarize_outlook(state: AgentState) -> AgentState:
    print("Agent 2: Summarizing sector/company outlook...")
    prompt = f"Summarize the sector and company outlook for '{state['ticker']}' from this data:\n{state['company_data']}"
    resp = llm.invoke([HumanMessage(content=prompt)])
    return {"summary": get_text(resp)}

def analyze_outlook(state: AgentState) -> AgentState:
    print("Agent 3: Analyzing outlook sentiment...")
    prompt = f"Is this company/sector outlook overall bullish or bearish?\n\n{state['summary']}"
    resp = llm.invoke([HumanMessage(content=prompt)])

    outlook = get_text(resp).strip().lower()
    label = "bullish" if "bullish" in outlook else "bearish"

    print(f"Outlook: {outlook} ({label})")
    return {"outlook": outlook, "outlook_label": label}

def investor_confidence_note(state: AgentState) -> AgentState:
    print("Agent 4A: Creating investor confidence note...")
    prompt = f"Write an investor-focused confidence note based on:\n{state['summary']}"
    resp = llm.invoke([HumanMessage(content=prompt)])
    return {"final_report": get_text(resp)}

def risk_watch_note(state: AgentState) -> AgentState:
    print("Agent 4B: Creating risk watch note...")
    prompt = f"Write a short risk-watch note for cautious investors based on:\n{state['summary']}"
    resp = llm.invoke([HumanMessage(content=prompt)])
    return {"final_report": get_text(resp)}

# --------------------------
# Build Graph
# --------------------------
workflow = StateGraph(AgentState)

workflow.add_node("fetch_company_data", fetch_company_data)
workflow.add_node("fetch_failed", fetch_failed)
workflow.add_node("summarize_outlook", summarize_outlook)
workflow.add_node("analyze_outlook", analyze_outlook)
workflow.add_node("investor_confidence_note", investor_confidence_note)
workflow.add_node("risk_watch_note", risk_watch_note)

workflow.set_entry_point("fetch_company_data")

# After fetch_company_data finishes, 
# check whether it succeeded or failed. 
# If it failed, go to fetch_failed. If it succeeded, go to summarize_outlook
workflow.add_conditional_edges(
    "fetch_company_data", # current node
    lambda state: "fetch_failed" # go to this node if the following condition is true
    if state["company_data"].startswith("Error fetching data") # if company data was not returned
    else "summarize_outlook" # if fetch was successful
)

workflow.add_edge("summarize_outlook", "analyze_outlook")

workflow.add_conditional_edges(
    "analyze_outlook",
    lambda state: "investor_confidence_note"
    if state["outlook_label"] == "bullish"
    else "risk_watch_note"
)

workflow.add_edge("fetch_failed", END)
workflow.add_edge("investor_confidence_note", END)
workflow.add_edge("risk_watch_note", END)

app = workflow.compile()

# --------------------------
# Run in a loop for multiple tickers
# --------------------------
if __name__ == "__main__":
    print("Enter a stock ticker (e.g. AAPL, MSFT, TSLA) for a sector/company outlook. Type 'exit' to quit.")

    while True:
        ticker = input("\nEnter ticker: ").strip()

        if ticker.lower() == "exit":
            print("Exiting...")
            break

        initial = {
            "ticker": ticker,
            "company_data": "",
            "summary": "",
            "outlook": "",
            "outlook_label": "",
            "final_report": "",
        }

        result = app.invoke(initial)

        print("\n" + "=" * 60)
        print(f"Ticker: {ticker}")
        print(result["final_report"])
        print("=" * 60)
