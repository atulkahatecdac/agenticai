# Two-stage retrieval on the help-desk FAQ (deck: "Two-Stage Retrieval").
#
#   Stage 1 - ChromaDB vector search returns 10 candidates (fast, high recall).
#             It compares two separately embedded vectors.
#   Stage 2 - a cross-encoder reranker reads the customer's question together
#             with each candidate's question AND answer, and scores the pair
#             (slower, more precise). Only the top few go to the user or LLM.
#
# Reranker: mixedbread-ai/mxbai-rerank-xsmall-v1 (local, ~150 MB download once).
# The second query shows the honest part: a reranker can also make things
# worse - always check one on your own data before switching it on.
#
# pip install chromadb sentence-transformers   (no API key)
import csv
import os

import chromadb
from sentence_transformers import CrossEncoder

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(BASE_DIR, "faq.csv"), encoding="utf-8") as f:
    FAQ = list(csv.DictReader(f))

client = chromadb.EphemeralClient()
faq = client.create_collection("faq_rerank")
faq.add(
    ids=[row["id"] for row in FAQ],
    documents=[row["question"] for row in FAQ],
    metadatas=[{"answer": row["answer"]} for row in FAQ],
)

reranker = CrossEncoder("mixedbread-ai/mxbai-rerank-xsmall-v1")


def two_stage(question: str, candidates: int = 10, show: int = 3):
    # Stage 1: vector search - cast a wide net
    hits = faq.query(query_texts=[question], n_results=candidates)
    found = list(zip(hits["documents"][0], [m["answer"] for m in hits["metadatas"][0]]))

    # Stage 2: score each (question, candidate) pair together
    scores = reranker.predict([(question, f"{q} {a}") for q, a in found])
    reranked = [pair for _, pair in sorted(zip(scores, found), key=lambda x: -x[0])]

    print(f'\nCustomer: "{question}"')
    print(f"  {'Vector search order':<44}After reranking")
    for (before, _), (after, _) in zip(found[:show], reranked[:show]):
        print(f"  {before:<44}{after}")
    print(f"  Reply: {reranked[0][1]}")


# "money back" = a refund, but vector search ranks the failed-payment entry first
two_stage("I want my money back")

# Here vector search was already right - the reranker prefers "wrong item"
two_stage("I bought shoes in the wrong size")
