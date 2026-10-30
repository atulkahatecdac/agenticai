import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

import os
import sys
import json
from typing import Annotated, TypedDict
from pydantic import BaseModel
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
# The PROMOTION process: how something said in SHORT-TERM memory (the
# in-thread message buffer, kept alive only by the checkpointer) ends
# up durable in LONG-TERM memory (a JSON file on disk, kept forever).
#
#   1. Every turn lives in short-term memory first - it's just the
#      next message appended to the thread's buffer.
#   2. After the agent replies, a small check asks: is anything in
#      this exchange worth keeping past this conversation? Most turns
#      say no.
#   3. If yes, that fact is WRITTEN to the long-term store. That write
#      is the promotion - it's the only thing that survives once the
#      thread is gone.
#
# The proof this isn't a dummy example: SESSION 2 below uses a brand
# new thread_id (empty short-term buffer) and the agent still knows
# the promoted fact - it can only have come from the long-term file.
#
# Scenario: a support assistant chatting with a user across two
# separate sessions.
# =====================================================================

LONG_TERM_PATH = os.path.join(os.path.dirname(__file__), "agent_memory", "long_term_memory.json")
os.makedirs(os.path.dirname(LONG_TERM_PATH), exist_ok=True)


def load_long_term_memory(user_id: str) -> list[str]:
    store = json.load(open(LONG_TERM_PATH, encoding="utf-8")) if os.path.exists(LONG_TERM_PATH) else {}
    return store.get(user_id, [])


def promote_to_long_term(user_id: str, fact: str):
    store = json.load(open(LONG_TERM_PATH, encoding="utf-8")) if os.path.exists(LONG_TERM_PATH) else {}
    existing = store.get(user_id, [])
    if fact not in existing:
        store[user_id] = existing + [fact]
    with open(LONG_TERM_PATH, "w", encoding="utf-8") as f:
        json.dump(store, f, indent=2)


class PromotionCheck(BaseModel):
    worth_remembering: bool
    fact: str | None  # the durable fact to promote, phrased standalone (null if worth_remembering is False)


promotion_llm = llm.with_structured_output(PromotionCheck)


class AgentState(TypedDict):
    user_id: str
    messages: Annotated[list, add_messages]
    long_term_facts: list[str]


# ---- Node 1: short-term memory is just state["messages"] - here we only pull in long-term ----
def load_memory(state: AgentState) -> AgentState:
    long_term_facts = load_long_term_memory(state["user_id"])
    print(f"  [long-term store has] {long_term_facts or 'nothing yet'}")
    return {"long_term_facts": long_term_facts}


# ---- Node 2: respond using short-term (messages) + whatever is in long-term ----
def generate_response(state: AgentState) -> AgentState:
    system = "You are a helpful support assistant."
    if state["long_term_facts"]:
        system += "\n\nThings you remember about this user from past sessions:\n" + \
                   "\n".join(f"- {f}" for f in state["long_term_facts"])

    response = llm.invoke([SystemMessage(content=system)] + state["messages"])
    return {"messages": [response]}


# ---- Node 3: the promotion step - short-term this turn, long-term if it matters ----
def maybe_promote(state: AgentState) -> AgentState:
    user_turn = state["messages"][-2].content

    check = promotion_llm.invoke([
        SystemMessage(content=(
            "Decide if this message contains a durable fact about the user worth "
            "remembering across future conversations (e.g. a name, preference, or "
            "recurring detail) - not a one-off question. If so, set worth_remembering=True "
            "and phrase it as a standalone fact in 'fact'."
        )),
        HumanMessage(content=user_turn),
    ])

    if check.worth_remembering and check.fact:
        promote_to_long_term(state["user_id"], check.fact)
        print(f"  [PROMOTED short-term -> long-term] {check.fact!r}")
    else:
        print("  [stays in short-term only] nothing durable in this turn")

    return {}


# Graph: START -> load_memory -> generate_response -> maybe_promote -> END
graph = StateGraph(AgentState)
graph.add_node("load_memory", load_memory)
graph.add_node("generate_response", generate_response)
graph.add_node("maybe_promote", maybe_promote)
graph.add_edge(START, "load_memory")
graph.add_edge("load_memory", "generate_response")
graph.add_edge("generate_response", "maybe_promote")
graph.add_edge("maybe_promote", END)

# The checkpointer holds SHORT-TERM memory - it resets to empty for any new thread_id.
app = graph.compile(checkpointer=MemorySaver())


def chat(user_id: str, thread_id: str, message: str) -> str:
    config = {"configurable": {"thread_id": thread_id}}
    result = app.invoke({"user_id": user_id, "messages": [HumanMessage(content=message)]}, config)
    return result["messages"][-1].content


if __name__ == "__main__":
    print("=" * 70)
    print("SESSION 1 (thread='session-1')")
    print("=" * 70)

    msg_1 = "Hi, I'm Meera and I prefer replies in bullet points, not paragraphs."
    print(f"\nUser: {msg_1}")
    print(f"Assistant: {chat('meera', 'session-1', msg_1)}")

    msg_2 = "What's the weather like for shipping delays this week?"
    print(f"\nUser: {msg_2}")
    print(f"Assistant: {chat('meera', 'session-1', msg_2)}")
    print("(^ just a one-off question - nothing new gets promoted)")

    print("\n" + "=" * 70)
    print("SESSION 2 (thread='session-2', NEW thread - short-term buffer is empty)")
    print("=" * 70)

    msg_3 = "Hi again, can you help me track my last order?"
    print(f"\nUser: {msg_3}")
    print(f"Assistant: {chat('meera', 'session-2', msg_3)}")
    print("(^ new thread has no short-term memory of session 1, yet the reply still comes as "
          "bullet points - that can only come from the LONG-TERM store the earlier turn promoted to)")
