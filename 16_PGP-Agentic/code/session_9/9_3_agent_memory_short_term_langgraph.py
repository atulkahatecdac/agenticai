# SHORT-TERM (working) memory: the message list of ONE conversation thread,
# kept by LangGraph's checkpointer (MemorySaver) under a thread_id.
# A new thread_id starts empty - nothing carries over between sessions
# unless it is written to long-term storage (see 9_4 to 9_7).

import sys
from typing import Annotated, TypedDict
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver

load_dotenv(override=True)
sys.stdout.reconfigure(encoding="utf-8")

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)


class State(TypedDict):
    messages: Annotated[list, add_messages]  # new messages are appended, not replaced


def respond(state: State) -> State:
    system = SystemMessage("You are an insurance claims assistant. Explain what a claim needs.")
    return {"messages": [llm.invoke([system] + state["messages"])]}


graph = StateGraph(State)
graph.add_node("respond", respond)
graph.add_edge(START, "respond")
graph.add_edge("respond", END)
app = graph.compile(checkpointer=MemorySaver())  # saves the message list per thread_id


def chat(thread_id: str, message: str):
    print(f"\n[{thread_id}] User: {message}")
    result = app.invoke({"messages": [HumanMessage(message)]}, {"configurable": {"thread_id": thread_id}})
    print(f"[{thread_id}] Assistant: {result['messages'][-1].content}")


chat("session-1", "My car got hit in a parking lot yesterday - minor bumper damage, no injuries. "
                  "Policy AUTO-4471-B. What do I need to submit to file a claim?")
chat("session-1", "Sorry, what documents did you just say I need again?")
print("(^ same thread: the agent remembers the previous turn)")

chat("session-2", "Sorry, what documents did you just say I need again?")
print("(^ new thread: empty history, so the agent has no idea what 'again' refers to)")
