# Agentic RAG: the MODEL decides whether to search, what to search for,
# and whether to search again. Search is just a tool it can call.
import json
import os
import psycopg
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(override=True)
client = OpenAI()
DATABASE_URL = os.environ["DATABASE_URL"]

MODEL = "gpt-4o-mini"
EMBED_MODEL = "text-embedding-3-small"
SYSTEM = (
    "You are DocAssist, the HR assistant of BlueRiver Software. "
    "Use search_documents for any question about company policy, and search "
    "again with a different query if the first results are not enough. "
    "Answer only from what you found and name the source file. "
    "For greetings or small talk, just answer without searching."
)

TOOLS = [
    {"type": "function", "function": {
        "name": "search_documents",
        "description": "Search the company's policy documents. Returns the most relevant passages.",
        "parameters": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "What to look for"}},
            "required": ["query"],
        },
    }},
    {"type": "function", "function": {
        "name": "list_documents",
        "description": "List the names of all documents in the knowledge base.",
        "parameters": {"type": "object", "properties": {}},
    }},
]


def search_documents(query, k=3):
    vector = client.embeddings.create(model=EMBED_MODEL, input=[query]).data[0].embedding
    with psycopg.connect(DATABASE_URL) as conn:
        rows = conn.execute(
            "SELECT source, content FROM chunks "
            "ORDER BY embedding <=> %s::vector LIMIT %s",
            (str(vector), k),
        ).fetchall()
    return "\n\n".join(f"[{source}]\n{content}" for source, content in rows)


def list_documents():
    with psycopg.connect(DATABASE_URL) as conn:
        rows = conn.execute("SELECT DISTINCT source FROM chunks ORDER BY source").fetchall()
    return ", ".join(row[0] for row in rows)


def run_agent(messages):
    for _ in range(5):   # at most 5 rounds of tool calls
        response = client.chat.completions.create(
            model=MODEL, messages=messages, tools=TOOLS)
        message = response.choices[0].message
        if not message.tool_calls:   # no tool wanted: this is the answer
            return message.content
        messages.append(message)
        for call in message.tool_calls:
            args = json.loads(call.function.arguments)
            print(f"   agent calls {call.function.name}({args})")
            if call.function.name == "search_documents":
                result = search_documents(**args)
            else:
                result = list_documents()
            messages.append({"role": "tool", "tool_call_id": call.id, "content": result})
    return "Sorry, I could not find an answer."


def ask(question):
    print("Q:", question)
    answer = run_agent([{"role": "system", "content": SYSTEM},
                        {"role": "user", "content": question}])
    print("A:", answer, "\n")


# Runs only when this file is started directly, not when 05a imports it
if __name__ == "__main__":
    ask("Hi, good morning!")                                # no search
    ask("What is the hotel limit in Pune?")                 # one search
    ask("I travel for work on a public holiday. What do I get, "
        "and by when must I use it?")                       # may search twice
    ask("Which documents can you answer from?")             # the other tool
