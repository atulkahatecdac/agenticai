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

# Trailing slash matters: "/books" (no slash) 301-redirects to "/books/",
# and that redirect hop has been observed to stall/time out - hitting the
# canonical "/books/" URL directly avoids the redirect altogether.
GUTENDEX_URL = "https://gutendex.com/books/"

@tool
def search_gutenberg_books(query: str) -> str:
    """Search Project Gutenberg's free ebook catalog via the Gutendex API
    (no key required). Input: a search term - title, author name, or
    subject, e.g. 'Jane Austen' or 'dragons'. Returns up to 5 matches as
    'Title by Author(s) [id=..., downloads=...]', one per line, ordered by
    popularity."""
    resp = requests.get(GUTENDEX_URL, params={"search": query}, timeout=10)
    resp.raise_for_status()
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

tools = [search_gutenberg_books]
tools_by_name = {t.name: t for t in tools}

# -----------------------------
# No ReAct here: bind_tools uses OpenAI's native function-calling instead
# of a hand-written Thought/Action/Observation prompt the model has to
# follow and we have to text-parse. The model either returns tool_calls
# or a plain answer - no prompt template, no AgentExecutor, no parsing
# errors to handle. The tradeoff is this loop only runs one round of
# tool calls before asking for a final answer; a multi-step ReAct-style
# agent can keep looping until it decides it's done.
# -----------------------------
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
llm_with_tools = llm.bind_tools(tools)

if __name__ == "__main__":
    question = (
        "Find Project Gutenberg's most downloaded free ebook by Jane Austen "
        "and tell me its title and download count."
    )

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
