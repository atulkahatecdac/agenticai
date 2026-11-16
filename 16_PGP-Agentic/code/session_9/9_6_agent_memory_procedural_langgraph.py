# Long-term PROCEDURAL memory: rules about HOW the agent should behave,
# learned from explicit user feedback, saved to a JSON file and added to
# every future system prompt. Unlike semantic memory (9_5) it is not a fact
# about the user - it changes the agent's own behaviour.
# Session 2 is a new thread, yet the agent still follows the session-1 rule.

import os
import sys
import json
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

MEMORY_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "agent_memory")
os.makedirs(MEMORY_DIR, exist_ok=True)
RULES_PATH = os.path.join(MEMORY_DIR, "procedural_memory.json")


def load_rules() -> dict:
    if not os.path.exists(RULES_PATH):
        return {}
    with open(RULES_PATH, encoding="utf-8") as f:
        return json.load(f)


class NewRule(BaseModel):
    rule: str  # a behaviour rule the user explicitly asked for, or ""


class State(TypedDict):
    user_id: str
    messages: Annotated[list, add_messages]


def respond(state: State) -> State:
    rules = load_rules().get(state["user_id"], [])
    print(f"  [loaded rules] {rules or 'none'}")
    system = "You are an insurance claims assistant. Explain what a claim needs."
    if rules:
        system += "\nBehaviour rules you MUST follow:\n" + "\n".join(f"- {r}" for r in rules)
    return {"messages": [llm.invoke([SystemMessage(system)] + state["messages"])]}


def save_rule(state: State) -> State:
    rule = llm.with_structured_output(NewRule).invoke(
        "If the user explicitly told the assistant how to behave from now on, state that rule; "
        f"otherwise return an empty string.\n\nUser: {state['messages'][-2].content}"
    ).rule
    rules = load_rules()
    if rule and rule not in rules.get(state["user_id"], []):
        rules.setdefault(state["user_id"], []).append(rule)
        with open(RULES_PATH, "w", encoding="utf-8") as f:
            json.dump(rules, f, indent=2)
        print(f"  [saved rule] {rule!r}")
    return {}


graph = StateGraph(State)
graph.add_node("respond", respond)
graph.add_node("save_rule", save_rule)
graph.add_edge(START, "respond")
graph.add_edge("respond", "save_rule")
graph.add_edge("save_rule", END)
app = graph.compile(checkpointer=MemorySaver())


def chat(thread_id: str, message: str):
    print(f"\n[{thread_id}] User: {message}")
    result = app.invoke({"user_id": "priya", "messages": [HumanMessage(message)]},
                        {"configurable": {"thread_id": thread_id}})
    print(f"[{thread_id}] Assistant: {result['messages'][-1].content}")


chat("session-1", "My car got hit in a parking lot yesterday - minor bumper damage. What do I need to file a claim?")
chat("session-1", "I have a hearing impairment, so please always send me written checklists "
                  "instead of asking me to call a phone number.")
chat("session-2", "I need to file another claim - my car window was smashed. What should I do next?")
print("(^ new thread - a written checklist instead of 'please call' shows the rule was remembered)")
