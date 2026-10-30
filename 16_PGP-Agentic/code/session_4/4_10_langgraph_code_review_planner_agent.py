# pip install langchain-openai langchain-core langgraph python-dotenv requests

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from dotenv import load_dotenv
from langgraph.graph import StateGraph, END
from typing import TypedDict
import os, requests

# --------------------------
# Shared State
# --------------------------
class AgentState(TypedDict):
    code_url: str
    code_content: str
    security_issues: str
    suggestions: str
    final_report: str
    next_action: str   # NEW: planner output

# --------------------------
# Setup
# --------------------------
load_dotenv(override=True)
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.1)

# --------------------------
# Helper: Fetch code
# --------------------------
def fetch_code(repo_url: str, path: str = "") -> str:
    repo_path = repo_url.replace("https://github.com/", "")
    api_url = f"https://api.github.com/repos/{repo_path}/contents/{path}"
    code_files = []

    try:
        response = requests.get(api_url)
        response.raise_for_status()
        items = response.json()
        for item in items:
            if item["type"] == "file" and item["name"].endswith(".java"):
                file_content = requests.get(item["download_url"]).text
                code_files.append(f"// {item['path']}\n{file_content}\n")
            elif item["type"] == "dir":
                code_files.append(fetch_code(repo_url, item["path"]))
        return "\n".join(code_files)[:10000]
    except Exception as e:
        return f"Error fetching code: {e}"

# --------------------------
# Agents
# --------------------------

def planner_agent(state: AgentState) -> AgentState:
    """Decides which step to execute next based on what's already done."""
    print("Planner: Deciding next action...")

    context = f"""
    Current state:
    - Code URL: {state['code_url']}
    - Security issues found: {bool(state['security_issues'])}
    - Suggestions added: {bool(state['suggestions'])}
    """

    prompt = f"""
    Based on the current state, decide what the next step should be.
    Choose one of the following actions:
    1. "review" → Fetch and analyze code for vulnerabilities.
    2. "suggest" → Provide fixes for found vulnerabilities.
    3. "finalize" → Generate the final executive report.
    4. "end" → If everything is complete.

    {context}

    Return only one word: review, suggest, finalize, or end.
    """

    resp = llm.invoke([HumanMessage(content=prompt)])
    next_action = resp.content.strip().lower()

    print(f"Planner decided next action: {next_action}")
    return {"next_action": next_action}


def security_review(state: AgentState) -> AgentState:
    print("Agent 1: Reviewing code for vulnerabilities...")
    code = fetch_code(state["code_url"])
    prompt = f"""
    Analyze this Java code for security vulnerabilities.

    Provide a brief structured report:
    - Vulnerability Type
    - Severity
    - Affected Code (line or snippet)
    - Suggested Fix
    Code:
    {code}
    """
    resp = llm.invoke([HumanMessage(content=prompt)])
    return {"code_content": code, "security_issues": resp.content}


def suggest_fixes(state: AgentState) -> AgentState:
    print("Agent 2: Suggesting fixes...")
    prompt = f"""
    You are a security engineer. Suggest clear, actionable fixes for each issue below.
    Issues:
    {state['security_issues']}
    """
    resp = llm.invoke([HumanMessage(content=prompt)])
    return {"suggestions": resp.content}


def finalize_report(state: AgentState) -> AgentState:
    print("Agent 3: Finalizing report...")
    prompt = f"""
    Create an executive security report for:
    {state['code_url']}

    Include:
    - Executive Summary
    - Key Vulnerabilities
    - Fix Recommendations
    - Risk Level
    - Next Steps

    Issues:
    {state['security_issues']}
    Suggestions:
    {state['suggestions']}
    """
    resp = llm.invoke([HumanMessage(content=prompt)])
    return {"final_report": resp.content}

# --------------------------
# Build Graph
# --------------------------
workflow = StateGraph(AgentState)

workflow.add_node("planner", planner_agent)
workflow.add_node("review", security_review)
workflow.add_node("suggest", suggest_fixes)
workflow.add_node("finalize", finalize_report)

# Set entry point
workflow.set_entry_point("planner")

# Conditional branching — true “agentic” behavior
workflow.add_conditional_edges(
    "planner",
    lambda s: s["next_action"],
    {
        "review": "review",
        "suggest": "suggest",
        "finalize": "finalize",
        "end": END
    }
)

# Static edges for normal linear flow
workflow.add_edge("review", "planner")
workflow.add_edge("suggest", "planner")
workflow.add_edge("finalize", END)

# Compile
app = workflow.compile()

# --------------------------
# Run
# --------------------------
if __name__ == "__main__":
    initial = {
        "code_url": "https://github.com/vulnerable-apps/verademo",
        "code_content": "",
        "security_issues": "",
        "suggestions": "",
        "final_report": "",
        "next_action": ""
    }

    print("=== Starting Agentic Security Review ===")
    result = app.invoke(initial)
    print("\n" + "=" * 60)
    print(result["final_report"])
    print("=" * 60)
