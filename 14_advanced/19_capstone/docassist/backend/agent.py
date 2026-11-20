# The agent: decides when to search, and remembers the conversation.
# Same loop as 04a_agentic_rag.py, plus the memory from 05a_memory.py.
import json
from openai import OpenAI

import database
import rag

client = OpenAI()
MODEL = "gpt-4o-mini"
SYSTEM = (
    "You are DocAssist, an assistant that answers questions about the documents "
    "in its knowledge base. Use search_documents for any question about their "
    "content, and search again with a different query if the first results are "
    "not enough. Answer only from what you found and name the source file. "
    "For greetings or small talk, just answer without searching."
)

TOOLS = [
    {"type": "function", "function": {
        "name": "search_documents",
        "description": "Search the uploaded documents. Returns the most relevant passages.",
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


def answer(session_id, question):
    history = database.load_history(session_id)   # short-term memory from Postgres
    messages = ([{"role": "system", "content": SYSTEM}] + history
                + [{"role": "user", "content": question}])
    steps = []   # what the agent did, shown in the UI

    reply = "Sorry, I could not find an answer."
    for _ in range(5):
        response = client.chat.completions.create(
            model=MODEL, messages=messages, tools=TOOLS)
        message = response.choices[0].message
        if not message.tool_calls:
            reply = message.content
            break
        messages.append(message)
        for call in message.tool_calls:
            args = json.loads(call.function.arguments)
            if call.function.name == "search_documents":
                rows = rag.search(args["query"])
                result = "\n\n".join(f"[{source}]\n{content}" for source, content in rows)
                steps.append(f"searched: {args['query']}")
            else:
                result = ", ".join(database.list_sources()) or "no documents yet"
                steps.append("listed documents")
            messages.append({"role": "tool", "tool_call_id": call.id, "content": result})

    database.save_message(session_id, "user", question)
    database.save_message(session_id, "assistant", reply)
    return reply, steps
