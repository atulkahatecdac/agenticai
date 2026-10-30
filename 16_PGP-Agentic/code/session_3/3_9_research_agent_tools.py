# pip install openai-agents tavily-python beautifulsoup4 requests python-dotenv

import os
import re
from datetime import date
import requests
from bs4 import BeautifulSoup
from agents import Agent, Runner, function_tool
from tavily import TavilyClient
from dotenv import load_dotenv

load_dotenv(override=True)

tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
REPORTS_DIR = os.path.join(os.path.dirname(__file__), "research_reports")

# =====================================================================
# Tool-augmented Research Agent, built on the OpenAI Agents SDK.
# Given a topic, the agent decides on its own when to call each tool:
# web_search (real Tavily search, can be called multiple times with
# different queries), get_current_date (so it frames "latest"/"current"
# correctly), and save_report (writes the final write-up to disk). The
# agent - not this script - decides the research plan and tool order.
# =====================================================================


@function_tool
def web_search(query: str) -> str:
    """Search the web for a query and return the top results (title, URL, short snippet)."""
    response = tavily_client.search(query=query, max_results=5)
    results = response.get("results", [])
    if not results:
        return f"No results found for '{query}'."
    return "\n".join(f"- {r['title']} ({r['url']}): {r['content'][:200]}" for r in results)


@function_tool
def fetch_page_content(url: str) -> str:
    """Fetch a specific URL and return its main readable text - use this to read a
    promising source in full when a web_search snippet is too short to be useful."""
    try:
        response = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()
    except Exception as e:
        return f"Could not fetch {url}: {e}"

    soup = BeautifulSoup(response.text, "html.parser")
    for tag in soup(["script", "style", "nav", "header", "footer"]):
        tag.decompose()

    text = " ".join(soup.get_text(separator=" ").split())
    return text[:3000] if text else "No readable text found on that page."


@function_tool
def get_current_date() -> str:
    """Return today's date - useful for framing how recent the research needs to be."""
    return date.today().isoformat()


@function_tool
def save_report(topic: str, content: str) -> str:
    """Save the final research report as a markdown file. Returns the saved file path."""
    os.makedirs(REPORTS_DIR, exist_ok=True)
    slug = re.sub(r"[^a-z0-9]+", "_", topic.lower()).strip("_")
    path = os.path.join(REPORTS_DIR, f"{slug}.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return f"Report saved to {path}"


research_agent = Agent(
    name="ResearchAgent",
    model="gpt-4o-mini",
    tools=[web_search, fetch_page_content, get_current_date, save_report],
    instructions="""
You are a research assistant. Given a topic:
1. Call get_current_date if the topic depends on recency (e.g. "latest", "current").
2. Call web_search one or more times, with different specific queries, to gather
   information from multiple sources - don't rely on a single search. If a result
   looks especially relevant but its snippet is too short to be useful, call
   fetch_page_content on its URL to read more of the actual page before relying on it.
3. Write a clear markdown report with a short summary, a "Key Findings" section
   (bulleted), and a "Sources" section listing the URLs you actually used.
4. Call the save_report tool with that markdown content - you have no file system or
   sandbox of your own, so the report only exists on disk if you actually call this tool.
5. Reply to the user with a brief summary and the exact file path returned by save_report.
   Never invent or guess a file path - only use the path the tool call actually returned.
""",
)


if __name__ == "__main__":
    topic = "What are the latest developments in AI agent frameworks in 2026?"
    result = Runner.run_sync(research_agent, topic)
    print(result.final_output)

    # Don't just trust the agent's claim that it saved a report - check the disk.
    # LLMs can describe having called a tool without actually calling it.
    saved_files = os.listdir(REPORTS_DIR) if os.path.isdir(REPORTS_DIR) else []
    if saved_files:
        print(f"\nVerified on disk: {os.path.join(REPORTS_DIR, saved_files[-1])}")
    else:
        print("\nWARNING: no report file found - save_report was never actually called.")
