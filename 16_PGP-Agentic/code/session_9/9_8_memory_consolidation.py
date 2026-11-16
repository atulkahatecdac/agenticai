# Memory consolidation: an episodic store (9_7) gains one raw episode per
# interaction, so near-duplicates about the same issue pile up. A periodic
# pass has an LLM group episodes that share a pattern, writes ONE summary per
# group, and swaps the summaries in for the raw episodes.
# 8 real rows from customer_support_qa_500.csv -> 3 patterns -> 3 summaries.

import os
import sys
import pandas as pd
import chromadb
from dotenv import load_dotenv
from pydantic import BaseModel
from langchain_openai import ChatOpenAI

load_dotenv(override=True)
sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
answers = pd.read_csv(os.path.join(BASE_DIR, "customer_support_qa_500.csv")).set_index("question")["answer"]

QUESTIONS = [
    # two-factor authentication trouble
    "My two-factor authenticator app isn't generating valid codes, what should I do?",
    "I lost my two-factor authentication device, how do I recover access?",
    "How do I fix two-factor codes not being accepted in the app?",
    # payment / card declined
    "Why was my payment declined?",
    "Why is my card being declined even though it has funds?",
    # subscription cancellation
    "How do I cancel my subscription?",
    "Can I pause my subscription instead of canceling it?",
    "How do I cancel a subscription I signed up for through the app store instead of the website?",
]
raw = [f"Customer asked: {q} | Resolution: {answers[q]}" for q in QUESTIONS]

store = chromadb.Client().create_collection("episodic_memory")
store.add(ids=[f"raw-{i}" for i in range(len(raw))], documents=raw)
print(f"BEFORE: {store.count()} raw episodes\n")


class Group(BaseModel):
    theme: str
    summary: str            # one 'Customer asked: ... | Resolution: ...' episode for the whole group
    source_indices: list[int]


class Consolidation(BaseModel):
    groups: list[Group]


llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
plan = llm.with_structured_output(Consolidation).invoke(
    "Group these support episodes by the recurring issue they describe (each index in exactly one "
    "group) and write one generalized summary episode per group:\n\n"
    + "\n".join(f"{i}. {e}" for i, e in enumerate(raw))
)
for g in plan.groups:
    print(f"[{g.theme}] episodes {g.source_indices}\n  -> {g.summary}\n")

store.delete(ids=store.get()["ids"])
store.add(ids=[f"summary-{i}" for i in range(len(plan.groups))], documents=[g.summary for g in plan.groups])
print(f"AFTER: {store.count()} consolidated episodes (from {len(raw)} raw)")
