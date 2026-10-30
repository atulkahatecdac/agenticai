import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

import os
import sys
import sqlite3
from typing import Annotated, TypedDict
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.sqlite import SqliteSaver

load_dotenv(override=True)
sys.stdout.reconfigure(encoding="utf-8")

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# =====================================================================
# The other agent_memory_*_langgraph.py examples hardcode thread_id
# strings like "session-1" / "session-2" to keep the demo readable.
# This one shows where that thread_id actually comes from in a real
# chat: it's the user's own username, typed in at the start - never
# hardcoded. The same username always maps to the same thread_id, so
# typing it again naturally REUSES that conversation; a different
# username starts a separate one.
#
# SqliteSaver (not MemorySaver) backs this, so reusing a username
# really does pick the conversation back up even after restarting
# this script - proving the reuse is real, not just re-run-in-process.
#
# (A raw username as thread_id is a simplification for this demo - a
# real app would still keep user_id and thread_id separate, as
# discussed in the other examples, to allow one user to have several
# concurrent conversations.)
# =====================================================================

DB_PATH = os.path.join(os.path.dirname(__file__), "agent_memory", "dynamic_session_chat.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]


def generate_response(state: AgentState) -> AgentState:
    system = SystemMessage(content="You are a helpful assistant.")
    response = llm.invoke([system] + state["messages"])
    return {"messages": [response]}


graph = StateGraph(AgentState)
graph.add_node("generate_response", generate_response)
graph.add_edge(START, "generate_response")
graph.add_edge("generate_response", END)


def chat(app, thread_id: str, message: str) -> str:
    config = {"configurable": {"thread_id": thread_id}}
    result = app.invoke({"messages": [HumanMessage(content=message)]}, config)
    return result["messages"][-1].content


if __name__ == "__main__":
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    app = graph.compile(checkpointer=SqliteSaver(conn))

    username = input("Enter your username: ").strip()
    thread_id = username

    prior_state = app.get_state({"configurable": {"thread_id": thread_id}})
    if prior_state.values.get("messages"):
        print(f"\nWelcome back, {username} - resuming your previous conversation.\n")
    else:
        print(f"\nHi {username}, starting a new conversation.\n")

    print("Type 'exit' to quit.\n")
    while True:
        user_message = input("You: ").strip()
        if user_message.lower() in ("exit", "quit"):
            break
        if not user_message:
            continue
        print(f"Assistant: {chat(app, thread_id, user_message)}\n")
