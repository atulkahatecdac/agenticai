# Episodic memory: a store of specific PAST episodes that GROWS as the agent
# works. A LangGraph graph runs recall -> respond -> remember: recall finds
# similar past cases, the agent answers using them, and remember writes the
# new Q and A back as another episode - so query 2 can recall query 1's episode.
# Seeded with 324 real support Q&A rows from customer_support_qa_500.csv.

import os
import sys
from typing import TypedDict
import pandas as pd
import chromadb
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END

load_dotenv(override=True)
sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
faq = pd.read_csv(os.path.join(BASE_DIR, "..", "..", "15_real", "customer_support_qa_500.csv"))

episodes = chromadb.Client().create_collection("episodic_memory")
seeds = [f"Customer asked: {r.question} | Resolution: {r.answer}" for r in faq.itertuples()]
episodes.add(ids=[f"seed-{i}" for i in range(len(seeds))], documents=seeds)
print(f"[seed] {len(seeds)} past support episodes stored")

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)


class State(TypedDict):
    query: str
    past: list[str]
    answer: str


def recall(state: State) -> dict:
    past = episodes.query(query_texts=[state["query"]], n_results=2)["documents"][0]
    print("[recall]\n" + "\n".join(f"  - {p}" for p in past))
    return {"past": past}


def respond(state: State) -> dict:
    answer = llm.invoke(
        "You are a customer support agent. Use these similar PAST resolved cases as guidance, "
        "but answer THIS customer's question.\n\nPast cases:\n" + "\n".join(f"- {p}" for p in state["past"])
        + f"\n\nCustomer question: {state['query']}"
    ).content
    return {"answer": answer}


def remember(state: State) -> dict:
    episodes.add(ids=[f"new-{episodes.count()}"],
                 documents=[f"Customer asked: {state['query']} | Resolution: {state['answer']}"])
    print("[remember] new episode stored")
    return {}


graph = StateGraph(State)
graph.add_node("recall", recall)
graph.add_node("respond", respond)
graph.add_node("remember", remember)
graph.add_edge(START, "recall")
graph.add_edge("recall", "respond")
graph.add_edge("respond", "remember")
graph.add_edge("remember", END)
app = graph.compile()

for query in [
    "My card keeps getting declined when I try to pay for my subscription, even though I have funds - what's going on?",
    "My subscription renewal payment is still getting declined, same issue as before - what should I do?",
]:
    print("\n" + "=" * 70 + f"\nQUERY: {query}")
    print(f"ANSWER: {app.invoke({'query': query})['answer']}")
print("(^ query 2 should recall the episode stored by query 1)")
