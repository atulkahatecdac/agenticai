# Swapping the embedding model (deck: "Popular Embedding Models").
#
# The same 48 help-desk questions (faq.csv) go into two collections:
#   - ChromaDB's default model, all-MiniLM-L6-v2 -> 384 numbers per question
#   - nomic-embed-text, running locally in Ollama -> 768 numbers per question
# Then the same customer questions are asked of both, and finally a query
# embedded with the WRONG model is sent - showing why documents and queries
# must use the same model.
#
# Needs a local Ollama server with the model pulled:  ollama pull nomic-embed-text
# No API key. Uses an in-memory client, so nothing is written to disk.
import csv
import os

import chromadb
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction, OllamaEmbeddingFunction

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(BASE_DIR, "faq.csv"), encoding="utf-8") as f:
    FAQ = list(csv.DictReader(f))

MODELS = {
    "all-MiniLM-L6-v2 (Chroma default)": DefaultEmbeddingFunction(),
    "nomic-embed-text (Ollama)": OllamaEmbeddingFunction(url="http://localhost:11434", model_name="nomic-embed-text"),
}

client = chromadb.EphemeralClient()
collections = {}
for i, (label, embed_fn) in enumerate(MODELS.items()):
    col = client.create_collection(f"faq_model_{i}", embedding_function=embed_fn)
    col.add(
        ids=[row["id"] for row in FAQ],
        documents=[row["question"] for row in FAQ],
        metadatas=[{"answer": row["answer"], "category": row["category"]} for row in FAQ],
    )
    dims = len(col.get(ids=["1"], include=["embeddings"])["embeddings"][0])
    print(f"{label}: {col.count()} questions, {dims} numbers per vector")
    collections[label] = col

for question in ["My parcel hasn't come yet - where is it?", "I want my money back"]:
    print(f'\nCustomer: "{question}"')
    for label, col in collections.items():
        hits = col.query(query_texts=[question], n_results=3)
        print(f"  {label}")
        for q, d in zip(hits["documents"][0], hits["distances"][0]):
            print(f"     {d:6.2f}  {q}")

# The rule: embed documents and queries with the same model.
# A 384-number MiniLM query cannot be compared with 768-number nomic vectors.
minilm_query = DefaultEmbeddingFunction()(["When will my order arrive?"])
try:
    collections["nomic-embed-text (Ollama)"].query(query_embeddings=minilm_query, n_results=1)
except Exception as e:
    print(f"\nMiniLM query against the nomic collection -> {type(e).__name__}: {e}")
