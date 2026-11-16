# Reranking: vector search is tuned for recall - it returns plausible
# candidates in a rough order. A reranker (cross-encoder) reads the query
# and each candidate TOGETHER, which is slower but far more accurate, so
# it only re-orders the short list the vector search already found.
# The KB mixes health, motor, life, travel and home insurance, so words
# like "claim" and "premium" pull in wrong-domain chunks for the reranker
# to push down.

import os
import sys
import json
import cohere
import chromadb
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv(override=True)
sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(BASE_DIR, "policy_documents.json"), encoding="utf-8") as f:
    documents = json.load(f)

kb = chromadb.Client().create_collection("policy_docs")
kb.add(ids=[str(i) for i in range(len(documents))], documents=documents)

co = cohere.ClientV2(api_key=os.getenv("COHERE_API_KEY"))
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)


def answer(question: str, docs: list[str]) -> str:
    context = "\n".join(f"- {d}" for d in docs)
    return llm.invoke(f"Answer using ONLY the context. Be concise.\n\nContext:\n{context}\n\nQuestion: {question}").content


QUESTIONS = [
    "What documents are required to file a cashless health insurance claim at a network "
    "hospital, and within what time should hospitalization be intimated to the insurer?",
    "Is a pre-existing disease covered immediately under a new health insurance policy, and "
    "what happens to my coverage if I miss paying my premium on the due date?",
]

for question in QUESTIONS:
    print("\n" + "=" * 70 + f"\nQUESTION: {question}\n" + "=" * 70)

    # BEFORE: top 10 by vector similarity
    result = kb.query(query_texts=[question], n_results=10)
    candidates = result["documents"][0]
    print("\nBEFORE - vector search, top 10:")
    for doc, dist in zip(candidates, result["distances"][0]):
        print(f"  distance={dist:.3f}  {doc}")

    # AFTER: rerank those same 10 and keep the best 3
    reranked = co.rerank(model="rerank-v4.0-pro", query=question, documents=candidates, top_n=3).results
    best = [candidates[r.index] for r in reranked]
    print("\nAFTER - Cohere rerank, top 3:")
    for r, doc in zip(reranked, best):
        print(f"  score={r.relevance_score:.3f}  {doc}")

    # The reordering changes what the LLM answers from
    print(f"\nANSWER from vector top 3:\n  {answer(question, candidates[:3])}")
    print(f"\nANSWER from reranked top 3:\n  {answer(question, best)}")
