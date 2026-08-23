import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

import os
import sys
import requests
from dotenv import load_dotenv
from serpapi import GoogleSearch
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.agents import create_tool_calling_agent, AgentExecutor

load_dotenv(override=True)

# Tool output can contain characters outside Windows' default console
# codepage (cp1252) - reconfigure stdout to UTF-8 so printing doesn't crash.
sys.stdout.reconfigure(encoding="utf-8")

# Trailing slash matters: "/books" (no slash) 301-redirects to "/books/",
# and that redirect hop has been observed to stall/time out - hitting the
# canonical "/books/" URL directly avoids the redirect altogether.
GUTENDEX_URL = "https://gutendex.com/books/"

@tool
def serp_search(query: str) -> str:
    """Search the live web via SerpAPI (Google results). Input: a search
    query, e.g. 'who wrote Pride and Prejudice'. Returns up to 5 results
    as 'Title (URL): snippet', one per line."""
    results = GoogleSearch({
        "engine": "google",
        "q": query,
        "api_key": os.environ["SERPAPI_API_KEY"],
    }).get_dict()

    organic = results.get("organic_results", [])[:5]
    if not organic:
        return f"No results found for '{query}'."
    return "\n".join(
        f"{r.get('title', '')} ({r.get('link', '')}): {r.get('snippet', '')}" for r in organic
    )

@tool
def search_gutenberg_books(query: str) -> str:
    """Search Project Gutenberg's free ebook catalog via the Gutendex API
    (no key required). Input: a search term - title, author name, or
    subject, e.g. 'Jane Austen' or 'dragons'. Returns up to 5 matches as
    'Title by Author(s) [id=..., downloads=...]', one per line, ordered by
    popularity."""
    try:
        resp = requests.get(GUTENDEX_URL, params={"search": query}, timeout=10)
        resp.raise_for_status()
    except requests.exceptions.RequestException as e:
        return f"Gutenberg search failed ({e}). Try again or answer without it."

    results = resp.json().get("results", [])
    if not results:
        return f"No Project Gutenberg books found for '{query}'."

    lines = []
    for book in results[:5]:
        authors = ", ".join(a["name"] for a in book.get("authors", [])) or "Unknown author"
        lines.append(
            f"{book['title']} by {authors} "
            f"[id={book['id']}, downloads={book.get('download_count', 0)}]"
        )
    return "\n".join(lines)

tools = [serp_search, search_gutenberg_books]

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful assistant with access to tools."),
    ("human", "{input}"),
    MessagesPlaceholder("agent_scratchpad"),
])

agent = create_tool_calling_agent(llm, tools, prompt)

# verbose=True prints every tool call/result as it happens - this IS the
# point of the demo: watching the agent pick between a live web search and
# the Gutenberg catalog tool depending on what the question needs.
agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    verbose=True,
    max_iterations=6,
)

if __name__ == "__main__":
    # Deliberately needs both tools: a live web fact (who wrote the book),
    # then a Gutenberg catalog lookup keyed off that author's name.
    question = (
        "Search the web to find out who wrote 'Pride and Prejudice'. Then look "
        "that author up on Project Gutenberg and tell me their most downloaded "
        "free ebook."
    )

    result = agent_executor.invoke({"input": question})

    print("\n" + "=" * 70)
    print("FINAL ANSWER")
    print("=" * 70)
    print(result["output"])
