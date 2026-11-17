import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

import sys
import requests
from dotenv import load_dotenv
from pydantic import BaseModel, Field
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

# -----------------------------
# Same tool as 06_1_tool_calling.py, but with its input schema spelled out as a
# Pydantic model (args_schema) instead of inferred from the function's
# type hints. This is the form to use once a tool takes more than one
# argument or needs per-field descriptions/validation beyond what a bare
# type hint can express - here, 'sentences' must be between 1 and 10.
# -----------------------------
class SearchWikipediaInput(BaseModel):
    topic: str = Field(description="Name of a person, place, thing or concept - the article name, not a question - e.g. 'Eiffel Tower'.")
    sentences: int = Field(default=4, ge=1, le=10, description="How many sentences of the article's introduction to return (1-10).")

@tool("search_wikipedia", args_schema=SearchWikipediaInput)
def search_wikipedia(topic: str, sentences: int = 4) -> str:
    """Look up a topic on Wikipedia (no key required). Returns the
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
        "exsentences": sentences,
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
# The other half of "pydantic version": instead of a free-text Final
# Answer string, the model's answer is forced into this schema via
# with_structured_output. No regex/string-parsing the answer back out -
# it arrives as a validated LandmarkAnswer instance or the call raises.
# -----------------------------
class LandmarkAnswer(BaseModel):
    name: str = Field(description="Name of the landmark.")
    city: str = Field(description="City the landmark is in.")
    designer: str = Field(description="Person or company that designed and built it.")
    year_completed: int = Field(description="Year construction was completed.")

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
llm_with_tools = llm.bind_tools(tools)
structured_llm = llm.with_structured_output(LandmarkAnswer)

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

    answer = structured_llm.invoke(messages)

    print("=" * 70)
    print("FINAL ANSWER (structured)")
    print("=" * 70)
    print(answer.model_dump_json(indent=2))
