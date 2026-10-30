import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

import os
import sys
import uuid
import chromadb
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
# LONG-TERM SEMANTIC memory - durable FACTS about the user (name,
# policy number, preferences, constraints), stored per user_id in a
# ChromaDB collection and retrieved by SEMANTIC SIMILARITY to the
# CURRENT message - real semantic search, not just "load everything
# for this user_id". Unlike short-term memory (see
# agent_memory_short_term_langgraph.py), this survives a brand-new
# conversation thread.
#
# The proof this isn't a dummy example: the demo below runs a SECOND,
# brand-new thread_id (a new session) and shows the agent already
# knowing a fact it was only told in the FIRST thread - that only
# works if the vector store is real and actually being queried.
#
# Scenario: an insurance claims assistant that should remember a
# policyholder's policy number across separate visits.
# =====================================================================

MEMORY_DIR = os.path.join(os.path.dirname(__file__), "agent_memory")
os.makedirs(MEMORY_DIR, exist_ok=True)

semantic_collection = chromadb.PersistentClient(
    path=os.path.join(MEMORY_DIR, "semantic_db")
).get_or_create_collection("semantic_facts")


def load_semantic_facts(user_id: str, current_message: str, top_k: int = 3) -> list[str]:
    if semantic_collection.count() == 0:
        return []
    results = semantic_collection.query(query_texts=[current_message], n_results=top_k, where={"user_id": user_id})
    return results["documents"][0] if results["documents"] else []


def save_semantic_facts(user_id: str, new_facts: list[str]):
    semantic_collection.add(
        ids=[str(uuid.uuid4()) for _ in new_facts],
        documents=new_facts,
        metadatas=[{"user_id": user_id}] * len(new_facts),
    )


# ---------------------------------------------------------------------
# Fact extraction: after each exchange, decide whether anything durable
# about the user was revealed. Most turns won't - a "what's the
# weather" aside shouldn't become a stored fact.
# ---------------------------------------------------------------------
class FactExtraction(BaseModel):
    new_facts: list[str]


extractor_llm = llm.with_structured_output(FactExtraction)


class AgentState(TypedDict):
    user_id: str
    messages: Annotated[list, add_messages]
    semantic_facts: list[str]


def load_long_term_memory(state: AgentState) -> AgentState:
    last_message = state["messages"][-1].content
    semantic_facts = load_semantic_facts(state["user_id"], last_message)
    print(f"  [loaded semantic facts] {semantic_facts or 'none'}")
    return {"semantic_facts": semantic_facts}


def generate_response(state: AgentState) -> AgentState:
    parts = ["You are a helpful insurance claims assistant. Help policyholders understand what "
             "documents, proof, or verification steps their claim needs."]
    if state["semantic_facts"]:
        parts.append("Known facts about this policyholder:\n" + "\n".join(f"- {f}" for f in state["semantic_facts"]))

    response = llm.invoke([SystemMessage(content="\n\n".join(parts))] + state["messages"])
    return {"messages": [response]}


def extract_and_save_facts(state: AgentState) -> AgentState:
    user_id = state["user_id"]
    user_turn, ai_turn = state["messages"][-2].content, state["messages"][-1].content

    extraction = extractor_llm.invoke([
        SystemMessage(content=(
            "From this exchange, extract new_facts - durable facts about the user worth "
            "remembering long-term, such as identifiers, preferences, or constraints "
            "(empty list if none)."
        )),
        HumanMessage(content=f"User: {user_turn}\nAssistant: {ai_turn}"),
    ])

    if extraction.new_facts:
        save_semantic_facts(user_id, extraction.new_facts)
        print(f"  [semantic memory saved] {extraction.new_facts}")

    return {}


# Graph: START -> load_long_term_memory -> generate_response -> extract_and_save_facts -> END
graph = StateGraph(AgentState)
graph.add_node("load_long_term_memory", load_long_term_memory)
graph.add_node("generate_response", generate_response)
graph.add_node("extract_and_save_facts", extract_and_save_facts)
graph.add_edge(START, "load_long_term_memory")
graph.add_edge("load_long_term_memory", "generate_response")
graph.add_edge("generate_response", "extract_and_save_facts")
graph.add_edge("extract_and_save_facts", END)

app = graph.compile(checkpointer=MemorySaver())


def chat(user_id: str, thread_id: str, message: str) -> str:
    config = {"configurable": {"thread_id": thread_id}}
    result = app.invoke({"user_id": user_id, "messages": [HumanMessage(content=message)]}, config)
    return result["messages"][-1].content


if __name__ == "__main__":
    print("=" * 70)
    print("SESSION 1 (thread='session-1') - policyholder filing a claim for the first time")
    print("=" * 70)

    print("\nUser: Hi, my car got hit in a parking lot yesterday - minor bumper damage, no "
          "injuries. My policy number is AUTO-4471-B. What do I need to submit to file a claim?")
    print(f"Assistant: {chat('priya', 'session-1', 'Hi, my car got hit in a parking lot yesterday - minor bumper damage, no injuries. My policy number is AUTO-4471-B. What do I need to submit to file a claim?')}")

    print("\n" + "=" * 70)
    print("SESSION 2 (thread='session-2', NEW thread - policyholder returns weeks later)")
    print("=" * 70)

    print("\nUser: Hi, I need to file another claim. Do you have my policy info on file?")
    print(f"Assistant: {chat('priya', 'session-2', 'Hi, I need to file another claim. Do you have my policy info on file?')}")
    print("(^ this is a NEW thread with an empty message list - correct policy-number recall "
          "here can only come from SEMANTIC memory)")
