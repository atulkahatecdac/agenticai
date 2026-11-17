import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

import sys
import requests
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_core.messages import BaseMessage, HumanMessage, ToolMessage

load_dotenv(override=True)

# Tool output can contain characters outside Windows' default console
# codepage (cp1252) - reconfigure stdout to UTF-8 so printing doesn't crash.
sys.stdout.reconfigure(encoding="utf-8")

# Wikipedia's public MediaWiki API - no key required. Wikimedia asks every
# client to send a descriptive User-Agent; requests without one may be blocked.
WIKIPEDIA_API_URL = "https://en.wikipedia.org/w/api.php"
HEADERS = {"User-Agent": "agenticai-course-demo/1.0 (educational script)"}

@tool
def search_wikipedia(topic: str) -> str:
    """Look up a topic on Wikipedia (no key required). Input: the name
    of a person, place, thing or concept - the article name, not a
    question - e.g. 'Eiffel Tower' or 'Ada Lovelace'. Returns the
    best-matching article's title, short description and the first few
    sentences of its introduction."""
    params = {
        "action": "query",
        "format": "json",
        "formatversion": 2,
        # Search first, then fetch the top hit's intro - all in one request.
        "generator": "search",
        "gsrsearch": topic,
        "gsrlimit": 1,
        "prop": "extracts|description",
        "exintro": 1,        # only the lead section
        "explaintext": 1,    # plain text, not HTML
        "exsentences": 4,
    }
    resp = requests.get(WIKIPEDIA_API_URL, params=params, headers=HEADERS, timeout=10)
    resp.raise_for_status()
    pages = resp.json().get("query", {}).get("pages", [])
    if not pages:
        return f"No Wikipedia article found for '{topic}'."

    page = pages[0]
    return (
        f"Title: {page['title']}\n"
        f"Description: {page.get('description') or 'n/a'}\n"
        f"Summary: {page.get('extract', '')}"
    )

tools = [search_wikipedia]
tools_by_name = {t.name: t for t in tools}

# -----------------------------
# No ReAct here: bind_tools uses OpenAI's native function-calling instead
# of a hand-written Thought/Action/Observation prompt the model has to
# follow and we have to text-parse. The model either returns tool_calls
# or a plain answer - no prompt template, no parsing errors to handle.
# The tradeoff is this code only runs one round of tool calls before
# asking for a final answer; 3_5_sql_database_toolkit_agent.py wraps the
# same idea in a loop that keeps going until the agent decides it's done.
# -----------------------------
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
llm_with_tools = llm.bind_tools(tools)

if __name__ == "__main__":
    question = "Using Wikipedia, tell me who designed and built the Eiffel Tower, and when."

    messages: list[BaseMessage] = [HumanMessage(question)]
    ai_message = llm_with_tools.invoke(messages)
    messages.append(ai_message)

    for tool_call in ai_message.tool_calls:
        print(f"Calling tool: {tool_call['name']}({tool_call['args']})")
        result = tools_by_name[tool_call["name"]].invoke(tool_call["args"])
        print(f"Tool result:\n{result}\n")
        messages.append(ToolMessage(content=result, tool_call_id=tool_call["id"]))

    final_message = llm_with_tools.invoke(messages) if ai_message.tool_calls else ai_message

    print("=" * 70)
    print("FINAL ANSWER")
    print("=" * 70)
    print(final_message.content)
