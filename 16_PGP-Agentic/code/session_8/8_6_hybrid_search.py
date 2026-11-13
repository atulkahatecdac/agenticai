import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")

import json
import os
import re
import shutil
import sys
from dotenv import load_dotenv
from rank_bm25 import BM25Okapi
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_openai import ChatOpenAI

load_dotenv(override=True)
sys.stdout.reconfigure(encoding="utf-8")

# =====================================================================
# Hybrid Search / Hybrid RAG: dense embedding search is great at
# matching MEANING even when the wording differs, but it can dilute
# exact terms (an acronym, a specific number, a policy name) into the
# surrounding semantic neighborhood. Sparse keyword search (BM25) is the
# opposite: it nails exact token overlap but has no notion of meaning -
# a paraphrase that avoids the KB's exact words scores poorly no matter
# how relevant it is. Hybrid search runs both retrievers over the same
# query and fuses their rankings - here with Reciprocal Rank Fusion
# (RRF): score(doc) = sum over retrievers of 1 / (k + rank_in_that_list)
# - so a document ranked highly by EITHER retriever rises to the top,
# without needing the two retrievers' raw scores to be on comparable
# scales.
#
# Knowledge base: the same 50-statement insurance policy KB used
# elsewhere in this folder. The two questions below are picked to each
# favor a different retriever - one leans on an exact acronym, the
# other is phrased in plain language that avoids the KB's own wording.
# =====================================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PERSIST_DIR = os.path.join(BASE_DIR, "hybrid_chroma_db")
shutil.rmtree(PERSIST_DIR, ignore_errors=True)

with open(os.path.join(BASE_DIR, "policy_documents.json"), encoding="utf-8") as f:
    POLICY_DOCUMENTS = json.load(f)

vectorstore = Chroma(
    collection_name="policy_docs",
    embedding_function=HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2"),
    persist_directory=PERSIST_DIR,
)
vectorstore.add_texts(POLICY_DOCUMENTS)


def tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


bm25 = BM25Okapi([tokenize(doc) for doc in POLICY_DOCUMENTS])

answer_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

RRF_K = 60
TOP_N = 3


def dense_ranking(query: str) -> list[str]:
    return [doc.page_content for doc in vectorstore.similarity_search(query, k=10)]


def sparse_ranking(query: str) -> list[str]:
    scores = bm25.get_scores(tokenize(query))
    ranked_indices = sorted(range(len(POLICY_DOCUMENTS)), key=lambda i: scores[i], reverse=True)
    return [POLICY_DOCUMENTS[i] for i in ranked_indices[:10]]


def reciprocal_rank_fusion(rankings: list[list[str]]) -> list[tuple[str, float]]:
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, doc in enumerate(ranking, start=1):
            scores[doc] = scores.get(doc, 0.0) + 1.0 / (RRF_K + rank)
    return sorted(scores.items(), key=lambda item: item[1], reverse=True)


def answer_from(label: str, question: str, docs: list[str]) -> None:
    context = "\n".join(f"- {d}" for d in docs)
    response = answer_llm.invoke(
        f"Answer the question using ONLY the context below. Be concise.\n\n"
        f"Context:\n{context}\n\nQuestion: {question}"
    )
    print(f"\n{label}\n  {response.content}")


QUESTIONS = [
    "What is the IRDAI mandated claim settlement timeline for health insurance?",

    "If my mom already had a health condition before we got this cover, will the insurance "
    "pay for treating it straight away?",
]

for question in QUESTIONS:
    print("\n" + "=" * 70)
    print(f"QUESTION: {question}")
    print("=" * 70)

    dense = dense_ranking(question)
    sparse = sparse_ranking(question)

    print(f"\nDENSE (embedding) top {TOP_N}:")
    for doc in dense[:TOP_N]:
        print(f"  - {doc}")

    print(f"\nSPARSE (BM25 keyword) top {TOP_N}:")
    for doc in sparse[:TOP_N]:
        print(f"  - {doc}")

    fused = reciprocal_rank_fusion([dense, sparse])
    print(f"\nHYBRID (RRF-fused) top {TOP_N}:")
    for doc, score in fused[:TOP_N]:
        print(f"  score={score:.4f}  {doc}")

    answer_from("DENSE-ONLY ANSWER:", question, dense[:TOP_N])
    answer_from("SPARSE-ONLY ANSWER:", question, sparse[:TOP_N])
    answer_from("HYBRID ANSWER:", question, [doc for doc, _ in fused[:TOP_N]])
