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
# LONG-TERM PROCEDURAL memory - durable rules about HOW the agent
# should behave, taught by explicit user feedback, stored per user_id
# and folded into every future session's system prompt until changed.
# Unlike semantic memory (see agent_memory_semantic_langgraph.py),
# this isn't a fact about the user - it's an instruction that reshapes
# the assistant's own behavior going forward.
#
# The proof this isn't a dummy example: the demo below runs a SECOND,
# brand-new thread_id (a new session) and shows the agent already
# following a behavior rule it was only given in the FIRST thread -
# that only works if the JSON store is real and actually being read.
#
# Scenario: an insurance claims assistant that a policyholder with a
# hearing impairment has asked to always follow up in writing instead
# of asking them to call.
# =====================================================================

MEMORY_DIR = os.path.join(os.path.dirname(__file__), "agent_memory")
os.makedirs(MEMORY_DIR, exist_ok=True)
PROCEDURAL_PATH = os.path.join(MEMORY_DIR, "procedural_memory.json")


def load_procedural_rules(user_id: str) -> list[str]:
    store = json.load(open(PROCEDURAL_PATH, encoding="utf-8")) if os.path.exists(PROCEDURAL_PATH) else {}
    return store.get(user_id, [])


def save_procedural_rule(user_id: str, rule: str):
    store = json.load(open(PROCEDURAL_PATH, encoding="utf-8")) if os.path.exists(PROCEDURAL_PATH) else {}
    existing = store.get(user_id, [])
    if rule not in existing:
        store[user_id] = existing + [rule]
    with open(PROCEDURAL_PATH, "w", encoding="utf-8") as f:
        json.dump(store, f, indent=2)


# ---------------------------------------------------------------------
# Rule extraction: after each exchange, decide whether the user gave
# explicit feedback about how the assistant should behave going
# forward. Most turns won't - only clear behavioral feedback counts.
# ---------------------------------------------------------------------
class RuleExtraction(BaseModel):
    new_procedural_rule: str | None


extractor_llm = llm.with_structured_output(RuleExtraction)


class AgentState(TypedDict):
    user_id: str
    messages: Annotated[list, add_messages]
    procedural_rules: list[str]


def load_long_term_memory(state: AgentState) -> AgentState:
    procedural_rules = load_procedural_rules(state["user_id"])
    print(f"  [loaded procedural rules] {procedural_rules or 'none'}")
    return {"procedural_rules": procedural_rules}


def generate_response(state: AgentState) -> AgentState:
    parts = ["You are a helpful insurance claims assistant. Help policyholders understand what "
             "documents, proof, or verification steps their claim needs."]
    if state["procedural_rules"]:
        parts.append("Behavior rules you MUST follow:\n" + "\n".join(f"- {r}" for r in state["procedural_rules"]))

    response = llm.invoke([SystemMessage(content="\n\n".join(parts))] + state["messages"])
    return {"messages": [response]}


def extract_and_save_rule(state: AgentState) -> AgentState:
    user_id = state["user_id"]
    user_turn, ai_turn = state["messages"][-2].content, state["messages"][-1].content

    extraction = extractor_llm.invoke([
        SystemMessage(content=(
            "From this exchange, extract new_procedural_rule - a new behavior rule ONLY if "
            "the user explicitly gave feedback about how the assistant should behave going "
            "forward (null otherwise)."
        )),
        HumanMessage(content=f"User: {user_turn}\nAssistant: {ai_turn}"),
    ])

    if extraction.new_procedural_rule:
        save_procedural_rule(user_id, extraction.new_procedural_rule)
        print(f"  [procedural memory saved] {extraction.new_procedural_rule!r}")

    return {}


# Graph: START -> load_long_term_memory -> generate_response -> extract_and_save_rule -> END
graph = StateGraph(AgentState)
graph.add_node("load_long_term_memory", load_long_term_memory)
graph.add_node("generate_response", generate_response)
graph.add_node("extract_and_save_rule", extract_and_save_rule)
graph.add_edge(START, "load_long_term_memory")
graph.add_edge("load_long_term_memory", "generate_response")
graph.add_edge("generate_response", "extract_and_save_rule")
graph.add_edge("extract_and_save_rule", END)

app = graph.compile(checkpointer=MemorySaver())


def chat(user_id: str, thread_id: str, message: str) -> str:
    config = {"configurable": {"thread_id": thread_id}}
    result = app.invoke({"user_id": user_id, "messages": [HumanMessage(content=message)]}, config)
    return result["messages"][-1].content


if __name__ == "__main__":
    print("=" * 70)
    print("SESSION 1 (thread='session-1') - policyholder gives a standing behavior instruction")
    print("=" * 70)

    print("\nUser: Hi, my car got hit in a parking lot yesterday - minor bumper damage, no "
          "injuries. What do I need to submit to file a claim?")
    print(f"Assistant: {chat('priya', 'session-1', 'Hi, my car got hit in a parking lot yesterday - minor bumper damage, no injuries. What do I need to submit to file a claim?')}")

    print("\nUser: One more thing - I have a hearing impairment, so please always send me "
          "written checklists instead of asking me to call a phone number.")
    print(f"Assistant: {chat('priya', 'session-1', 'One more thing - I have a hearing impairment, so please always send me written checklists instead of asking me to call a phone number.')}")

    print("\n" + "=" * 70)
    print("SESSION 2 (thread='session-2', NEW thread - policyholder returns weeks later)")
    print("=" * 70)

    print("\nUser: Hi, I need to file another claim - my car window was smashed in a different "
          "parking lot. What should I do next?")
    print(f"Assistant: {chat('priya', 'session-2', 'Hi, I need to file another claim - my car window was smashed in a different parking lot. What should I do next?')}")
    print("(^ this is a NEW thread - a written checklist here (not 'please call...') proves "
          "PROCEDURAL memory carried over rather than the rule being restated)")
