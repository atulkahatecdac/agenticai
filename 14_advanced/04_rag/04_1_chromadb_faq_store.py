# Step 1 of the help-desk FAQ example used by every 04_rag script (deck: "What Is a
# Vector Embedding?" and "Storing the FAQ in ChromaDB"). Adapted from
# 9_general/rag/rag_1_chroma_db_basic.py and rag_5_chroma_db_adding_metadata_to_query_chroma_embeddings.py.
#
#   - Stores the first four questions of faq.csv (an online shop's help desk -
#     48 entries in all) in a persistent ChromaDB collection; four keep the output short
#   - Only the QUESTION is embedded; the answer and category go into metadata
#   - Prints what an embedding looks like, and how the collection is configured
#
# No API key: ChromaDB embeds with its default local model, all-MiniLM-L6-v2
# (downloaded once, ~80 MB). Run 04_2_chromadb_faq_query.py next.
import csv
import os

import chromadb

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(BASE_DIR, "faq.csv"), encoding="utf-8") as f:
    FAQ = list(csv.DictReader(f))[:4]

# PersistentClient saves to disk, so 04_2 can open the same collection later.
# (chromadb.Client() would keep everything in memory and lose it on exit.)
client = chromadb.PersistentClient(path=os.path.join(BASE_DIR, "chroma_db"))

# Start fresh on every run
try:
    client.delete_collection("faq")
except Exception:
    pass

# Defaults: all-MiniLM-L6-v2 embeddings, an HNSW index, squared L2 distance.
# For cosine instead: client.create_collection("faq", configuration={"hnsw": {"space": "cosine"}})
faq = client.create_collection("faq")

faq.add(
    ids=[f["id"] for f in FAQ],
    documents=[f["question"] for f in FAQ],                       # embedded
    metadatas=[{"answer": f["answer"], "category": f["category"]} for f in FAQ],  # stored as is
)
print(f"Stored {faq.count()} FAQ entries in collection '{faq.name}'\n")

# What did ChromaDB actually store? Embeddings are only returned when asked for.
stored = faq.get(include=["documents", "embeddings", "metadatas"])
for doc_id, question, vector, meta in zip(stored["ids"], stored["documents"], stored["embeddings"], stored["metadatas"]):
    first3 = ", ".join(f"{x:.2f}" for x in vector[:3])
    print(f"id {doc_id}: {question}")
    print(f"   vector: [{first3}, ...]  ({len(vector)} numbers)")
    print(f"   metadata: {meta}\n")

hnsw = faq.configuration_json["hnsw"]
print(f"Index: HNSW, distance = {hnsw['space']}, up to {hnsw['max_neighbors']} neighbours per vector")
