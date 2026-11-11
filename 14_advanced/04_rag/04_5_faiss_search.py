# The help-desk FAQ in FAISS (deck: "ChromaDB or FAISS?" and "Choosing a FAISS Index").
#
# FAISS is a search library, not a database: you embed the questions yourself,
# FAISS stores only the vectors, and a search returns ROW NUMBERS - you look
# the question and answer up in your own data. The same vectors go into two
# index types:
#   - IndexFlatL2          exact: compares the query with every vector
#   - IndexHNSWFlat(.., 32) approximate: the graph index ChromaDB uses
# Same model (all-MiniLM-L6-v2) and metric (squared L2) as ChromaDB, so the
# distances match 04_2's.
#
# pip install faiss-cpu sentence-transformers   (no API key)
import csv
import os

import faiss
from sentence_transformers import SentenceTransformer

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(BASE_DIR, "faq.csv"), encoding="utf-8") as f:
    FAQ = list(csv.DictReader(f))
questions = [row["question"] for row in FAQ]

# 1. You embed (ChromaDB did this for you)
model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
embeddings = model.encode(questions, convert_to_numpy=True).astype("float32")   # 48 x 384
dimension = embeddings.shape[1]

# 2. Build two indexes over the same vectors
flat = faiss.IndexFlatL2(dimension)          # exact
hnsw = faiss.IndexHNSWFlat(dimension, 32)    # approximate graph, up to 32 links per vector
for index in (flat, hnsw):
    index.add(embeddings)                    # a vector's only identity is its row number
print(f"Vectors stored: {flat.ntotal} of {dimension} numbers each\n")


def search(index, query, k=3):
    query_vector = model.encode([query], convert_to_numpy=True).astype("float32")
    distances, rows = index.search(query_vector, k)
    # 3. FAISS returns row numbers - you look up the text
    return [(round(float(d), 2), FAQ[r]["question"], FAQ[r]["answer"]) for d, r in zip(distances[0], rows[0])]


for query in ["My parcel hasn't come yet - where is it?", "I want my money back"]:
    exact, approx = search(flat, query), search(hnsw, query)
    print(f'Customer: "{query}"')
    for d, q, _ in exact:
        print(f"   {d:5.2f}  {q}")
    print(f"   HNSW returns the same top 3: {[q for _, q, _ in approx] == [q for _, q, _ in exact]}")
    print(f"   Reply: {exact[0][2]}\n")
