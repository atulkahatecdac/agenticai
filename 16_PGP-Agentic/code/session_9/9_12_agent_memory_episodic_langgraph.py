import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

import os
import sys
from typing import Annotated, TypedDict
import chromadb
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
# LONG-TERM EPISODIC memory - durable records of specific past
# situations and how they were resolved, stored in a ChromaDB
# collection and retrieved by semantic similarity to the CURRENT
# message, so a new-but-similar situation can recall precedent. This
# is different from semantic memory (see
# agent_memory_semantic_langgraph.py), which stores plain facts rather
# than whole resolved situations, and is looked up by similarity
# rather than by user_id alone.
#
# The proof this isn't a dummy example: the demo below runs a SECOND,
# brand-new thread_id (a new session, a DIFFERENT claim) and shows the
# agent recalling what a SIMILAR earlier claim required - that only
# works if the vector store is real and actually being queried.
#
# Scenario: an insurance claims assistant that recalls what proof was
# required for a similar past claim from the same policyholder.
# =====================================================================

MEMORY_DIR = os.path.join(os.path.dirname(__file__), "agent_memory")
os.makedirs(MEMORY_DIR, exist_ok=True)

episodic_collection = chromadb.PersistentClient(
    path=os.path.join(MEMORY_DIR, "episodic_db")
).get_or_create_collection("episodes")


def retrieve_episodic_memories(user_id: str, current_message: str, top_k: int = 2) -> list[str]:
    if episodic_collection.count() == 0:
        return []
    results = episodic_collection.query(query_texts=[current_message], n_results=top_k, where={"user_id": user_id})
    return results["documents"][0] if results["documents"] else []


def save_episode(user_id: str, summary: str):
    episodic_collection.add(
        ids=[f"{user_id}-{episodic_collection.count()}"], documents=[summary], metadatas=[{"user_id": user_id}]
    )


# ---------------------------------------------------------------------
# Episode extraction: after each exchange, decide whether it was a
# concrete resolved situation worth recalling later. Small talk or a
# simple question shouldn't become an episode.
# ---------------------------------------------------------------------
class EpisodeExtraction(BaseModel):
    episode_summary: str | None


extractor_llm = llm.with_structured_output(EpisodeExtraction)


class AgentState(TypedDict):
    user_id: str
    messages: Annotated[list, add_messages]
    episodic_context: list[str]


def load_long_term_memory(state: AgentState) -> AgentState:
    last_message = state["messages"][-1].content
    episodic_context = retrieve_episodic_memories(state["user_id"], last_message)
    print(f"  [loaded episodic context] {episodic_context or 'none'}")
    return {"episodic_context": episodic_context}


def generate_response(state: AgentState) -> AgentState:
    parts = ["You are a helpful insurance claims assistant. Help policyholders understand what "
             "documents, proof, or verification steps their claim needs."]
    if state["episodic_context"]:
        parts.append("Similar past claims from this policyholder and what was required to resolve them:\n"
                      + "\n".join(f"- {e}" for e in state["episodic_context"]))

    response = llm.invoke([SystemMessage(content="\n\n".join(parts))] + state["messages"])
    return {"messages": [response]}


def extract_and_save_episode(state: AgentState) -> AgentState:
    user_id = state["user_id"]
    user_turn, ai_turn = state["messages"][-2].content, state["messages"][-1].content

    extraction = extractor_llm.invoke([
        SystemMessage(content=(
            "From this exchange, extract episode_summary - a short summary of this exchange as "
            "a resolved episode ONLY if it's a concrete task/situation worth recalling if "
            "something similar comes up later (null for small talk or simple facts)."
        )),
        HumanMessage(content=f"User: {user_turn}\nAssistant: {ai_turn}"),
    ])

    if extraction.episode_summary:
        save_episode(user_id, extraction.episode_summary)
        print(f"  [episodic memory saved] {extraction.episode_summary!r}")

    return {}


# Graph: START -> load_long_term_memory -> generate_response -> extract_and_save_episode -> END
graph = StateGraph(AgentState)
graph.add_node("load_long_term_memory", load_long_term_memory)
graph.add_node("generate_response", generate_response)
graph.add_node("extract_and_save_episode", extract_and_save_episode)
graph.add_edge(START, "load_long_term_memory")
graph.add_edge("load_long_term_memory", "generate_response")
graph.add_edge("generate_response", "extract_and_save_episode")
graph.add_edge("extract_and_save_episode", END)

app = graph.compile(checkpointer=MemorySaver())


def chat(user_id: str, thread_id: str, message: str) -> str:
    config = {"configurable": {"thread_id": thread_id}}
    result = app.invoke({"user_id": user_id, "messages": [HumanMessage(content=message)]}, config)
    return result["messages"][-1].content


if __name__ == "__main__":
    print("=" * 70)
    print("SESSION 1 (thread='session-1') - policyholder files and resolves a claim")
    print("=" * 70)

    print("\nUser: Hi, my car got hit in a parking lot yesterday - minor bumper damage, no "
          "injuries. What do I need to submit to file a claim?")
    print(f"Assistant: {chat('priya', 'session-1', 'Hi, my car got hit in a parking lot yesterday - minor bumper damage, no injuries. What do I need to submit to file a claim?')}")

    print("\nUser: Got it - I'll send photos of the damage and a copy of the police report.")
    print(f"Assistant: {chat('priya', 'session-1', 'Got it - I will send photos of the damage and a copy of the police report.')}")

    print("\n" + "=" * 70)
    print("SESSION 2 (thread='session-2', NEW thread - a different but similar claim, weeks later)")
    print("=" * 70)

    print("\nUser: I need to file another claim - my car window was smashed in a different "
          "parking lot. What kind of proof did I need to provide last time for something similar?")
    print(f"Assistant: {chat('priya', 'session-2', 'I need to file another claim - my car window was smashed in a different parking lot. What kind of proof did I need to provide last time for something similar?')}")
    print("(^ this is a NEW thread - recall of the earlier bumper-damage claim's document "
          "requirements can only come from EPISODIC memory, retrieved by similarity)")
