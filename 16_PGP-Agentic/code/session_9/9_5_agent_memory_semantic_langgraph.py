# Long-term SEMANTIC memory: durable FACTS about the user (policy number,
# preferences...), stored in ChromaDB and recalled by similarity to the
# current message. Unlike short-term memory (9_3) it survives a new thread:
# session 2 starts empty, yet the agent knows the policy number from session 1.

import os
import sys
import uuid
import chromadb
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
facts_db = chromadb.PersistentClient(path=os.path.join(MEMORY_DIR, "semantic_db")).get_or_create_collection("semantic_facts")


class Facts(BaseModel):
    new_facts: list[str]


class State(TypedDict):
    user_id: str
    messages: Annotated[list, add_messages]


def respond(state: State) -> State:
    facts = []
    if facts_db.count():
        facts = facts_db.query(query_texts=[state["messages"][-1].content], n_results=3,
                               where={"user_id": state["user_id"]})["documents"][0]
    print(f"  [recalled facts] {facts or 'none'}")
    system = "You are an insurance claims assistant. Explain what a claim needs."
    if facts:
        system += "\nKnown facts about this policyholder:\n" + "\n".join(f"- {f}" for f in facts)
    return {"messages": [llm.invoke([SystemMessage(system)] + state["messages"])]}


def save_facts(state: State) -> State:
    facts = llm.with_structured_output(Facts).invoke(
        "List durable facts about the user worth remembering long-term (identifiers, preferences, "
        f"constraints), or an empty list:\n\nUser: {state['messages'][-2].content}"
    ).new_facts
    if facts:
        facts_db.add(ids=[str(uuid.uuid4()) for _ in facts], documents=facts,
                     metadatas=[{"user_id": state["user_id"]}] * len(facts))
        print(f"  [saved facts] {facts}")
    return {}


graph = StateGraph(State)
graph.add_node("respond", respond)
graph.add_node("save_facts", save_facts)
graph.add_edge(START, "respond")
graph.add_edge("respond", "save_facts")
graph.add_edge("save_facts", END)
app = graph.compile(checkpointer=MemorySaver())


def chat(thread_id: str, message: str):
    print(f"\n[{thread_id}] User: {message}")
    result = app.invoke({"user_id": "priya", "messages": [HumanMessage(message)]},
                        {"configurable": {"thread_id": thread_id}})
    print(f"[{thread_id}] Assistant: {result['messages'][-1].content}")


chat("session-1", "My car got hit in a parking lot yesterday - minor bumper damage, no injuries. "
                  "My policy number is AUTO-4471-B. What do I need to submit to file a claim?")
chat("session-2", "Hi, I need to file another claim. Do you have my policy info on file?")
print("(^ new, empty thread - the policy number can only come from semantic memory)")
