# pip install pandas scikit-learn sentence-transformers numpy
import os
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer

# -----------------------------
# Load data
# -----------------------------
CSV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "documents.csv")
df = pd.read_csv(CSV_PATH)
documents = df["text"].tolist()

# -----------------------------
# 1. Keyword search: TF-IDF + cosine similarity
# Scores documents by overlapping words - strong on exact terms, acronyms,
# and names that embeddings can blur together (e.g. "ELSS", "SIP").
# -----------------------------
tfidf = TfidfVectorizer()
tfidf_matrix = tfidf.fit_transform(documents)

def keyword_scores(query):
    query_vec = tfidf.transform([query])
    return cosine_similarity(query_vec, tfidf_matrix)[0]

# -----------------------------
# 2. Semantic search: sentence embeddings + cosine similarity
# Scores documents by meaning - finds paraphrases that share no words
# with the query at all (e.g. "put money away for old age" -> "retirement").
# -----------------------------
print("Loading embedding model...")
model = SentenceTransformer("all-MiniLM-L6-v2")
doc_embeddings = model.encode(documents, convert_to_numpy=True, show_progress_bar=True)

def semantic_scores(query):
    query_embedding = model.encode([query], convert_to_numpy=True)
    return cosine_similarity(query_embedding, doc_embeddings)[0]

# -----------------------------
# 3a. Fusion method 1: Weighted Average of Scoring
# Normalize both score sets to a common [0, 1] range, then blend them.
# TF-IDF cosine and embedding cosine are not on comparable scales, so
# combining raw scores would let one signal dominate.
# alpha=1.0 -> pure semantic, alpha=0.0 -> pure keyword
# -----------------------------
def normalize(scores):
    min_s, max_s = scores.min(), scores.max()
    if max_s - min_s < 1e-9:
        return np.zeros_like(scores)
    return (scores - min_s) / (max_s - min_s)

def weighted_hybrid_search(query, top_k=3, alpha=0.5):
    kw = normalize(keyword_scores(query))
    sem = normalize(semantic_scores(query))
    combined = alpha * sem + (1 - alpha) * kw

    top_indices = np.argsort(combined)[::-1][:top_k]

    print(f"\n[Weighted Average] Query: '{query}'  (alpha={alpha} -> {alpha:.0%} semantic / {1-alpha:.0%} keyword)")
    print("-" * 70)
    for rank, idx in enumerate(top_indices, start=1):
        print(
            f"{rank}. [combined={combined[idx]:.3f} semantic={sem[idx]:.3f} keyword={kw[idx]:.3f}] "
            f"({df['category'][idx]}) {documents[idx]}"
        )

# -----------------------------
# 3b. Fusion method 2: Reciprocal Rank Fusion (RRF)
# Ignores the actual scores and uses each result's RANK in its own list
# instead. This sidesteps the scale-mismatch problem entirely - a document
# ranked #1 by both keyword and semantic search wins, regardless of what
# the raw cosine/TF-IDF numbers were. k=60 is the standard damping
# constant from the original RRF paper; it flattens the gap between
# rank 1 and rank 2 so one method can't dominate on a lucky top score.
# -----------------------------
def reciprocal_rank_fusion(query, top_k=3, k=60):
    kw = keyword_scores(query)
    sem = semantic_scores(query)

    kw_rank = {idx: rank for rank, idx in enumerate(np.argsort(kw)[::-1], start=1)}
    sem_rank = {idx: rank for rank, idx in enumerate(np.argsort(sem)[::-1], start=1)}

    rrf_scores = np.array([
        1 / (k + kw_rank[i]) + 1 / (k + sem_rank[i])
        for i in range(len(documents))
    ])

    top_indices = np.argsort(rrf_scores)[::-1][:top_k]

    print(f"\n[RRF] Query: '{query}'  (k={k})")
    print("-" * 70)
    for rank, idx in enumerate(top_indices, start=1):
        print(
            f"{rank}. [rrf={rrf_scores[idx]:.5f} kw_rank={kw_rank[idx]} sem_rank={sem_rank[idx]}] "
            f"({df['category'][idx]}) {documents[idx]}"
        )

# -----------------------------
# Demo queries
# -----------------------------
if __name__ == "__main__":
    # Balanced hybrid: query shares words with some docs AND means the same as others
    weighted_hybrid_search("SIP investment plan", alpha=0.5)
    reciprocal_rank_fusion("SIP investment plan")

    # No shared words with the best match - keyword search alone would miss this,
    # semantic search finds it via meaning
    weighted_hybrid_search("put money away for old age", alpha=0.5)
    reciprocal_rank_fusion("put money away for old age")

    # Same query, keyword-only vs semantic-only, to see each signal in isolation
    weighted_hybrid_search("ELSS", alpha=0.0)
    weighted_hybrid_search("ELSS", alpha=1.0)
