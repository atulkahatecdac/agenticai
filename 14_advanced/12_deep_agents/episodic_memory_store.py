import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

import os
import shutil
import sys
from typing import TypedDict
from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langgraph.graph import StateGraph, START, END

load_dotenv(override=True)
sys.stdout.reconfigure(encoding="utf-8")

# =====================================================================
# Episodic memory: unlike a static RAG corpus, the store starts with a
# few seed episodes and then GROWS from the agent's own interactions -
# remember() writes each resolved case back into the vector DB, so a
# later, similar case can recall() it. Backed by a real persistent
# Chroma DB on disk (not an in-memory list), so the memory genuinely
# outlives a single run - reset here only so this demo is repeatable.
# =====================================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PERSIST_DIR = os.path.join(BASE_DIR, "episodic_memory_db")
shutil.rmtree(PERSIST_DIR, ignore_errors=True)

vectorstore = Chroma(
    collection_name="episodic_memory",
    embedding_function=OpenAIEmbeddings(model="text-embedding-3-small"),
    persist_directory=PERSIST_DIR,
)
vectorstore.add_texts([
    "Customer asked: My debit card was declined at a store even though I have money in my account. | "
    "Resolution: Confirmed the merchant category (online gambling) was blocked by the account's default "
    "security settings; walked the customer through allowing that category via Card Settings > Merchant Controls.",
    "Customer asked: I was charged twice for the same purchase at the same store. | "
    "Resolution: Identified it as a duplicate authorization hold, not two real charges; explained the pending "
    "hold clears automatically within 3-5 business days once the merchant settles the transaction.",
    "Customer asked: My card got declined at an ATM twice while I was on a trip abroad. | "
    "Resolution: Explained the $500 daily ATM withdrawal limit and enabled travel notification on the "
    "account so future foreign-country transactions aren't flagged as suspicious.",
])

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)


class EpisodicState(TypedDict):
    query: str
    retrieved_episodes: list[str]
    response: str


def recall(state: EpisodicState) -> EpisodicState:
    matches = vectorstore.similarity_search(state["query"], k=2)
    episodes = [m.page_content for m in matches]
    print(f"[recall] {len(episodes)} similar past episode(s) found")
    return {"retrieved_episodes": episodes}


def respond(state: EpisodicState) -> EpisodicState:
    context = "\n\n".join(f"- {e}" for e in state["retrieved_episodes"]) or "(no similar past cases found)"
    prompt = f"""You are a bank customer support agent. Use these similar PAST resolved cases as
guidance for a consistent answer, but address THIS customer's specific question.

Past similar cases:
{context}

Current customer question: {state['query']}"""
    response = llm.invoke(prompt)
    return {"response": response.content}


def remember(state: EpisodicState) -> EpisodicState:
    episode = f"Customer asked: {state['query']} | Resolution: {state['response']}"
    vectorstore.add_texts([episode])
    print("[remember] new episode stored in the vector DB")
    return {}


graph = StateGraph(EpisodicState)
graph.add_node("recall", recall)
graph.add_node("respond", respond)
graph.add_node("remember", remember)
graph.add_edge(START, "recall")
graph.add_edge("recall", "respond")
graph.add_edge("respond", "remember")
graph.add_edge("remember", END)

app = graph.compile()

if __name__ == "__main__":
    # Query 1: close to a SEED episode (ATM abroad) - recall should find it.
    print("=" * 70)
    print("QUERY 1")
    print("=" * 70)
    result1 = app.invoke({
        "query": "My debit card keeps getting declined at ATMs while I'm on vacation in Italy, what's going on?",
        "retrieved_episodes": [], "response": "",
    })
    print(f"Response: {result1['response']}\n")

    # Query 2: close to query 1's OWN just-written episode, not just the
    # original seed data - proving the store actually grew and is used.
    print("=" * 70)
    print("QUERY 2 (should also recall the episode just written from query 1)")
    print("=" * 70)
    result2 = app.invoke({
        "query": "I'm traveling to France next month and worried my card will get declined at ATMs again like last time.",
        "retrieved_episodes": [], "response": "",
    })
    print("Retrieved episodes:")
    for ep in result2["retrieved_episodes"]:
        print(f"  - {ep}")
    print(f"\nResponse: {result2['response']}")
