# Hybrid search on the help-desk FAQ (deck: "Hybrid Search" and "Inside 04_8_hybrid_search.py").
#
# Each FAQ entry is scored two ways, then the scores are fused:
#   - keyword:  TF-IDF + cosine over question + answer - exact words, acronyms
#               and codes ("NEFT"), which often appear only in the answer text
#   - semantic: embeddings of the questions (as in every 04 script) - meaning,
#               paraphrases with no shared words
#   - fusion:   weighted average of normalised scores, or Reciprocal Rank Fusion
#
# pip install pandas scikit-learn sentence-transformers numpy   (no API key)
import os

import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# -----------------------------
# Load the FAQ
# -----------------------------
CSV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "faq.csv")
df = pd.read_csv(CSV_PATH)
questions = df["question"].tolist()
full_text = (df["question"] + " " + df["answer"]).tolist()

# -----------------------------
# 1. Keyword search: TF-IDF + cosine similarity
# Scores entries by overlapping words - strong on exact terms, acronyms and
# codes that embeddings can blur together (e.g. "NEFT", "GSTIN").
# -----------------------------
tfidf = TfidfVectorizer()
tfidf_matrix = tfidf.fit_transform(full_text)


def keyword_scores(query):
    return cosine_similarity(tfidf.transform([query]), tfidf_matrix)[0]


# -----------------------------
# 2. Semantic search: sentence embeddings + cosine similarity
# Scores entries by meaning - finds paraphrases that share no words with the
# query at all (e.g. "a bill for my company" -> "Can I get a GST invoice?").
# -----------------------------
print("Loading embedding model...")
model = SentenceTransformer("all-MiniLM-L6-v2")
doc_embeddings = model.encode(questions, convert_to_numpy=True)


def semantic_scores(query):
    return cosine_similarity(model.encode([query], convert_to_numpy=True), doc_embeddings)[0]


def show(label, query, scores, extra):
    print(f"\n[{label}] Query: '{query}'")
    print("-" * 78)
    for rank, idx in enumerate(np.argsort(scores)[::-1][:3], start=1):
        print(f"{rank}. [{extra(idx)}] ({df['category'][idx]}) {df['question'][idx]}")


# -----------------------------
# 3a. Fusion method 1: weighted average of scores
# Normalise both score sets to [0, 1], then blend them. TF-IDF cosine and
# embedding cosine are not on comparable scales, so raw scores would let one
# signal dominate. alpha=1.0 -> pure semantic, alpha=0.0 -> pure keyword.
# -----------------------------
def normalize(scores):
    lo, hi = scores.min(), scores.max()
    return np.zeros_like(scores) if hi - lo < 1e-9 else (scores - lo) / (hi - lo)


def weighted_hybrid_search(query, alpha=0.5):
    kw, sem = normalize(keyword_scores(query)), normalize(semantic_scores(query))
    combined = alpha * sem + (1 - alpha) * kw
    show(f"Weighted, alpha={alpha} -> {alpha:.0%} semantic / {1 - alpha:.0%} keyword", query, combined,
         lambda i: f"combined={combined[i]:.2f} semantic={sem[i]:.2f} keyword={kw[i]:.2f}")


# -----------------------------
# 3b. Fusion method 2: Reciprocal Rank Fusion (RRF)
# Ignore the raw scores and use only each method's RANK: sum 1/(k + rank).
# Like a real system, each method contributes only its own top results
# (top_n, and only entries it actually matched); an entry missing from a list
# gets nothing from that method.
# k=60 is the usual constant from the original RRF paper; it flattens the gap
# between rank 1 and rank 2 so one method can't dominate on a lucky top score.
# -----------------------------
def top_ranks(scores, top_n):
    best = [i for i in np.argsort(scores)[::-1][:top_n] if scores[i] > 0]
    return {idx: r for r, idx in enumerate(best, start=1)}


def reciprocal_rank_fusion(query, k=60, top_n=10):
    kw_rank = top_ranks(keyword_scores(query), top_n)
    sem_rank = top_ranks(semantic_scores(query), top_n)
    rrf = np.zeros(len(questions))
    for ranks in (kw_rank, sem_rank):
        for idx, r in ranks.items():
            rrf[idx] += 1 / (k + r)
    show(f"RRF, k={k}, top {top_n} from each", query, rrf,
         lambda i: f"rrf={rrf[i]:.4f} kw_rank={kw_rank.get(i, '-')} sem_rank={sem_rank.get(i, '-')}")


# -----------------------------
# Demo queries
# -----------------------------
if __name__ == "__main__":
    # Balanced: shares words with the right entry AND means the same - both agree
    weighted_hybrid_search("How do I cancel my order?")
    reciprocal_rank_fusion("How do I cancel my order?")

    # No useful words in common with the right entry - semantic carries it
    weighted_hybrid_search("can I get a bill for my company", alpha=0.0)
    weighted_hybrid_search("can I get a bill for my company", alpha=1.0)
    weighted_hybrid_search("can I get a bill for my company", alpha=0.5)
    reciprocal_rank_fusion("can I get a bill for my company")

    # An acronym that appears only in one answer - keyword carries it
    weighted_hybrid_search("NEFT", alpha=0.0)
    weighted_hybrid_search("NEFT", alpha=1.0)
    # The 50/50 blend keeps the right entry first: it also scores mid-range on meaning.
    # RRF ties here - each method's #1 is missing from the other's top 10, and RRF
    # sees only ranks. That is the trade-off: RRF needs no score tuning, the weighted
    # average uses how strong each match is.
    weighted_hybrid_search("NEFT", alpha=0.5)
    reciprocal_rank_fusion("NEFT")
