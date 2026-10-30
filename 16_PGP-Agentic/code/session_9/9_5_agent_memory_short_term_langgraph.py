import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

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

# =====================================================================
# SHORT-TERM (working) memory - the running message list for ONE
# conversation thread, kept by LangGraph's checkpointer (MemorySaver).
# It lets the agent recall what was just said within a thread, but it
# is gone the moment a new thread_id starts - nothing here survives
# across sessions unless something writes it to long-term storage
# (see agent_memory_semantic_langgraph.py / _episodic_ / _procedural_).
#
# Scenario: an insurance claims assistant answering a follow-up
# question within the same conversation, then starting a brand-new
# thread to prove that recall doesn't carry over.
# =====================================================================


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]


def generate_response(state: AgentState) -> AgentState:
    system = SystemMessage(content="You are a helpful insurance claims assistant. Help policyholders "
                                    "understand what documents, proof, or verification steps their claim needs.")
    response = llm.invoke([system] + state["messages"])
    return {"messages": [response]}


graph = StateGraph(AgentState)
graph.add_node("generate_response", generate_response)
graph.add_edge(START, "generate_response")
graph.add_edge("generate_response", END)

# The checkpointer is what makes messages behave as SHORT-TERM (thread-scoped)
# memory - a new thread_id starts with an empty message list no matter what.

# After each "invoke" call, the checkpointer writes the 
# resulting full message list to its in-process dictionary.
# This is keyed by thread_id, and is re-initialized for each new thread_id.
# We do not have to worry about this in a multi-threaded context.
app = graph.compile(checkpointer=MemorySaver())


def chat(thread_id: str, message: str) -> str:
    config = {"configurable": {"thread_id": thread_id}}
    result = app.invoke({"messages": [HumanMessage(content=message)]}, config)
    return result["messages"][-1].content


if __name__ == "__main__":
    print("=" * 70)
    print("THREAD 'session-1' - two turns in the same conversation")
    print("=" * 70)

    print("\nUser: Hi, my car got hit in a parking lot yesterday - minor bumper damage, no "
          "injuries. My policy number is AUTO-4471-B. What do I need to submit to file a claim?")
    print(f"Assistant: {chat('session-1', 'Hi, my car got hit in a parking lot yesterday - minor bumper damage, no injuries. My policy number is AUTO-4471-B. What do I need to submit to file a claim?')}")

    print("\nUser: Sorry, what documents did you just say I need again?")
    print(f"Assistant: {chat('session-1', 'Sorry, what documents did you just say I need again?')}")
    print("(^ answered correctly - SHORT-TERM memory recalls prior turns within the same thread)")

    print("\n" + "=" * 70)
    print("THREAD 'session-2' - a brand-new thread, no shared history")
    print("=" * 70)

    print("\nUser: Sorry, what documents did you just say I need again?")
    print(f"Assistant: {chat('session-2', 'Sorry, what documents did you just say I need again?')}")
    print("(^ the agent has no idea what 'again' refers to - a new thread_id starts with an "
          "empty message list, proving this memory is thread-scoped, not durable)")
