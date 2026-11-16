# Promoting SHORT-TERM memory to EXTERNAL long-term memory (a SQLite file):
#   1. every turn lives in the thread's message list (checkpointer)
#   2. after replying, an LLM check asks: is there a durable fact about the user here?
#   3. if yes, it is INSERTed into SQLite - that write is the "promotion"
# Session 2 uses a new thread (empty short-term memory), yet the agent still
# knows the fact - it can only have come from SQLite.

import os
import sys
import sqlite3
from typing import Annotated, TypedDict
from dotenv import load_dotenv
from pydantic import BaseModel
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver

load_dotenv(override=True)
sys.stdout.reconfigure(encoding="utf-8")

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "agent_memory", "external_memory.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
db = sqlite3.connect(DB_PATH, check_same_thread=False)
db.execute("CREATE TABLE IF NOT EXISTS facts (user_id TEXT, fact TEXT, UNIQUE(user_id, fact))")


class Promotion(BaseModel):
    worth_remembering: bool
    fact: str  # standalone fact, or "" if nothing worth keeping


class State(TypedDict):
    user_id: str
    messages: Annotated[list, add_messages]


def respond(state: State) -> State:
    facts = [r[0] for r in db.execute("SELECT fact FROM facts WHERE user_id = ?", (state["user_id"],))]
    print(f"  [SQLite has] {facts or 'nothing yet'}")
    system = "You are a helpful support assistant."
    if facts:
        system += "\nWhat you remember about this user:\n" + "\n".join(f"- {f}" for f in facts)
    return {"messages": [llm.invoke([SystemMessage(system)] + state["messages"])]}


def maybe_promote(state: State) -> State:
    check = llm.with_structured_output(Promotion).invoke(
        "Does this message contain a durable fact about the user worth remembering in future "
        "conversations (name, preference, recurring detail) - not a one-off question?\n\n"
        + state["messages"][-2].content
    )
    if check.worth_remembering and check.fact:
        db.execute("INSERT OR IGNORE INTO facts VALUES (?, ?)", (state["user_id"], check.fact))
        db.commit()
        print(f"  [PROMOTED to SQLite] {check.fact!r}")
    else:
        print("  [stays short-term only]")
    return {}


graph = StateGraph(State)
graph.add_node("respond", respond)
graph.add_node("maybe_promote", maybe_promote)
graph.add_edge(START, "respond")
graph.add_edge("respond", "maybe_promote")
graph.add_edge("maybe_promote", END)
app = graph.compile(checkpointer=MemorySaver())  # short-term: resets for every new thread_id


def chat(thread_id: str, message: str):
    print(f"\n[{thread_id}] User: {message}")
    result = app.invoke({"user_id": "meera", "messages": [HumanMessage(message)]},
                        {"configurable": {"thread_id": thread_id}})
    print(f"[{thread_id}] Assistant: {result['messages'][-1].content}")


chat("session-1", "Hi, I'm Meera and I prefer replies in bullet points, not paragraphs.")
chat("session-1", "What's the weather like for shipping delays this week?")
chat("session-2", "Hi again, can you help me track my last order?")
print("(^ new thread, yet the reply uses bullet points - that came from SQLite)")

print("\nThe SQLite table, queried directly:")
for row in db.execute("SELECT * FROM facts"):
    print(f"  {row}")
