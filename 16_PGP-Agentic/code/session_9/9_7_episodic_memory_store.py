# Episodic memory: a store of specific PAST episodes that GROWS as the agent
# works. recall() finds similar past cases, the agent answers using them, and
# remember() writes the new Q and A back as another episode - so query 2 can
# recall the episode query 1 just created.
# Seeded with 324 real support Q&A rows from customer_support_qa_500.csv.

import os
import sys
import pandas as pd
import chromadb
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv(override=True)
sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
faq = pd.read_csv(os.path.join(BASE_DIR, "customer_support_qa_500.csv"))

episodes = chromadb.Client().create_collection("episodic_memory")
seeds = [f"Customer asked: {r.question} | Resolution: {r.answer}" for r in faq.itertuples()]
episodes.add(ids=[f"seed-{i}" for i in range(len(seeds))], documents=seeds)
print(f"[seed] {len(seeds)} past support episodes stored")

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)


def recall(query: str) -> list[str]:
    return episodes.query(query_texts=[query], n_results=2)["documents"][0]


def remember(query: str, answer: str):
    episodes.add(ids=[f"new-{episodes.count()}"], documents=[f"Customer asked: {query} | Resolution: {answer}"])
    print("[remember] new episode stored")


def handle(query: str):
    print("\n" + "=" * 70 + f"\nQUERY: {query}")
    past = recall(query)
    print("[recall]\n" + "\n".join(f"  - {p}" for p in past))
    answer = llm.invoke(
        "You are a customer support agent. Use these similar PAST resolved cases as guidance, "
        "but answer THIS customer's question.\n\nPast cases:\n" + "\n".join(f"- {p}" for p in past)
        + f"\n\nCustomer question: {query}"
    ).content
    print(f"ANSWER: {answer}")
    remember(query, answer)


handle("My card keeps getting declined when I try to pay for my subscription, even though I have funds - what's going on?")
handle("My subscription renewal payment is still getting declined, same issue as before - what should I do?")
print("(^ query 2 should recall the episode stored by query 1)")
