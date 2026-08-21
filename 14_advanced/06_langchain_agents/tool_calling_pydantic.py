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

# Trailing slash matters: "/books" (no slash) 301-redirects to "/books/",
# and that redirect hop has been observed to stall/time out - hitting the
# canonical "/books/" URL directly avoids the redirect altogether.
GUTENDEX_URL = "https://gutendex.com/books/"

# -----------------------------
# Same tool as tool_calling.py, but with its input schema spelled out as a
# Pydantic model (args_schema) instead of inferred from the function's
# type hints. Functionally identical - this is just the explicit form,
# useful once a tool takes more than one argument or needs per-field
# descriptions/validation beyond what a bare type hint can express.
# -----------------------------
class SearchGutenbergInput(BaseModel):
    query: str = Field(description="A search term - title, author name, or subject, e.g. 'Jane Austen' or 'dragons'.")

@tool("search_gutenberg_books", args_schema=SearchGutenbergInput)
def search_gutenberg_books(query: str) -> str:
    """Search Project Gutenberg's free ebook catalog via the Gutendex API
    (no key required). Returns up to 5 matches as 'Title by Author(s)
    [id=..., downloads=...]', one per line, ordered by popularity."""
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
# The other half of "pydantic version": instead of a free-text Final
# Answer string, the model's answer is forced into this schema via
# with_structured_output. No regex/string-parsing the answer back out -
# it arrives as a validated BookAnswer instance or the call raises.
# -----------------------------
class BookAnswer(BaseModel):
    title: str = Field(description="Title of the book.")
    author: str = Field(description="Author of the book.")
    download_count: int = Field(description="Number of times the book has been downloaded.")

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
llm_with_tools = llm.bind_tools(tools)
structured_llm = llm.with_structured_output(BookAnswer)

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

    answer = structured_llm.invoke(messages)

    print("=" * 70)
    print("FINAL ANSWER (structured)")
    print("=" * 70)
    print(answer.model_dump_json(indent=2))
