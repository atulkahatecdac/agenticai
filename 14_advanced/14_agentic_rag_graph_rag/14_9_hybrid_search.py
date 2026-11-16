# Hybrid search: run a keyword retriever (BM25) and a semantic retriever
# (vectors) on the same query, then fuse their rankings.
#   BM25    - nails exact words and acronyms, but knows nothing about meaning
#   vectors - match meaning across different wording, but blur exact terms
# Reciprocal Rank Fusion: score(doc) = sum of 1 / (k + rank in each list),
# so a document ranked highly by EITHER retriever rises to the top.
# Question 1 leans on an acronym (BM25 wins), question 2 on paraphrase (vectors win).

import os
import re
import sys
import json
import chromadb
from dotenv import load_dotenv
from rank_bm25 import BM25Okapi
from langchain_openai import ChatOpenAI

load_dotenv(override=True)
sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(BASE_DIR, "policy_documents.json"), encoding="utf-8") as f:
    documents = json.load(f)

kb = chromadb.Client().create_collection("policy_docs")
kb.add(ids=[str(i) for i in range(len(documents))], documents=documents)


def tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


bm25 = BM25Okapi([tokenize(d) for d in documents])
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
TOP_N = 3


def semantic_search(query: str) -> list[str]:
    return kb.query(query_texts=[query], n_results=10)["documents"][0]


def keyword_search(query: str) -> list[str]:
    scores = bm25.get_scores(tokenize(query))
    return [doc for _, doc in sorted(zip(scores, documents), reverse=True)[:10]]


def reciprocal_rank_fusion(rankings: list[list[str]], k: int = 60) -> list[str]:
    scores = {}
    for ranking in rankings:
        for rank, doc in enumerate(ranking, start=1):
            scores[doc] = scores.get(doc, 0) + 1 / (k + rank)
    return sorted(scores, key=scores.get, reverse=True)


def answer(question: str, docs: list[str]) -> str:
    context = "\n".join(f"- {d}" for d in docs)
    return llm.invoke(f"Answer using ONLY the context. Be concise.\n\nContext:\n{context}\n\nQuestion: {question}").content


QUESTIONS = [
    "What is the IRDAI mandated claim settlement timeline for health insurance?",
    "If my mom already had a health condition before we got this cover, will the insurance "
    "pay for treating it straight away?",
]

for question in QUESTIONS:
    print("\n" + "=" * 70 + f"\nQUESTION: {question}\n" + "=" * 70)
    semantic = semantic_search(question)
    keyword = keyword_search(question)
    hybrid = reciprocal_rank_fusion([semantic, keyword])

    for label, ranking in [("SEMANTIC", semantic), ("KEYWORD (BM25)", keyword), ("HYBRID (RRF)", hybrid)]:
        print(f"\n{label} top {TOP_N}:")
        for doc in ranking[:TOP_N]:
            print(f"  - {doc}")
        print(f"  ANSWER: {answer(question, ranking[:TOP_N])}")
