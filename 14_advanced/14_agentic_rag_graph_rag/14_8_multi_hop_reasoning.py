# Multi-hop reasoning: some answers need a CHAIN of facts that sit in
# different chunks (the rule, a timing condition, who processes it, how
# long it takes). One similarity search returns chunks that resemble the
# question's wording and can't notice a link is missing. Multi-hop loops:
# retrieve -> decide what's still missing -> search for that -> repeat.

import os
import sys
import json
import chromadb
from dotenv import load_dotenv
from pydantic import BaseModel
from langchain_openai import ChatOpenAI

load_dotenv(override=True)
sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(BASE_DIR, "policy_documents.json"), encoding="utf-8") as f:
    documents = json.load(f)

kb = chromadb.Client().create_collection("policy_docs")
kb.add(ids=[str(i) for i in range(len(documents))], documents=documents)

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
MAX_HOPS = 4


class HopDecision(BaseModel):
    done: bool           # enough facts to answer every part of the question?
    missing: str         # what is still unanswered
    next_hop_query: str  # a search for the ONE missing fact ("" if done)


def search(query: str, k: int) -> list[str]:
    return kb.query(query_texts=[query], n_results=k)["documents"][0]


def multi_hop_retrieve(question: str) -> list[str]:
    facts, query = [], question
    for hop in range(1, MAX_HOPS + 1):
        new = [d for d in search(query, k=2) if d not in facts]
        if not new:
            break
        facts += new
        print(f"  [hop {hop}] {query!r}\n" + "\n".join(f"      + {d}" for d in new))

        decision = llm.with_structured_output(HopDecision).invoke(
            f"Question: {question}\n\nFacts so far:\n" + "\n".join(f"- {f}" for f in facts)
            + "\n\nAre these enough to answer every part of the question, including checking any "
            "number or timing in it against a rule? If not, give a search for the ONE next fact needed."
        )
        print(f"      missing: {decision.missing}")
        if decision.done:
            break
        query = decision.next_hop_query
    return facts


def answer(question: str, docs: list[str]) -> str:
    context = "\n".join(f"- {d}" for d in docs)
    return llm.invoke(
        "Answer using ONLY the context. If the question gives a number or timing, first check it "
        f"against the relevant rule. Be concise.\n\nContext:\n{context}\n\nQuestion: {question}"
    ).content


QUESTIONS = [
    "I'm on a Family Floater Gold health insurance plan and had an emergency hospitalization at "
    "a network hospital. I got the hospitalization intimated to the insurer 20 hours after "
    "admission and want a cashless claim - will it be accepted, who processes it, and how long "
    "will settlement take once all documents are in?",
    "My mother is a senior citizen on a health insurance policy with a co-payment clause. She "
    "was treated for a planned surgery at a hospital that is NOT in the insurer's network, and "
    "she intimated the insurer 40 hours in advance. Will her claim be cashless or reimbursement, "
    "will she have to pay a share herself, and within how many days after discharge must she "
    "submit her bills?",
]

for question in QUESTIONS:
    print("\n" + "=" * 70 + f"\nQUESTION: {question}\n" + "=" * 70)

    single = search(question, k=3)
    print("\nBEFORE - one search, top 3:\n" + "\n".join(f"  - {d}" for d in single))
    print(f"  ANSWER: {answer(question, single)}")

    print("\nAFTER - multi-hop:")
    print(f"  ANSWER: {answer(question, multi_hop_retrieve(question))}")
