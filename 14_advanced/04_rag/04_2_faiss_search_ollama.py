# pip install faiss-cpu ollama
# Requires a local Ollama server running with the embedding model pulled:
#   ollama pull nomic-embed-text

import ollama
import faiss
import numpy as np

EMBED_MODEL = "nomic-embed-text"

# -------------------------------------------------------
# Sample Documents
# -------------------------------------------------------
documents = [
    "Machine learning is a subset of Artificial Intelligence.",
    "Python is a popular programming language.",
    "The Taj Mahal is located in Agra.",
    "Neural networks are inspired by the human brain.",
    "The capital of France is Paris.",
    "FAISS is a library for similarity search.",
    "Large Language Models are trained on huge datasets.",
    "Cricket is one of the most popular sports in India.",
    "Pandas is used for data analysis in Python.",
    "ChromaDB is a vector database."
]

# -------------------------------------------------------
# Generate Embeddings
# -------------------------------------------------------
print("Generating embeddings...")

# 10 x 768 array for 10 documents (nomic-embed-text's native dimension)
embeddings = np.array(
    ollama.embed(model=EMBED_MODEL, input=documents).embeddings,
    dtype="float32"
)

# -------------------------------------------------------
# Create FAISS Index
# -------------------------------------------------------
dimension = embeddings.shape[1]

# Append raw vectors into a flat list for L2 (Euclidean distance) comparison
# The only identity a vector has is its row position (0, 1, 2, ...) - the order which they were added in
index = faiss.IndexFlatL2(dimension)
# Other options: IndexFlatIP, IndexHNSW32, IndexHNSW64

index.add(embeddings)

print(f"Number of vectors stored = {index.ntotal}")

# -------------------------------------------------------
# Search Function
# -------------------------------------------------------
def semantic_search(query, top_k=3):

    query_embedding = np.array(
        ollama.embed(model=EMBED_MODEL, input=[query]).embeddings,
        dtype="float32"
    )

    # L2 (Euclidean distance) between query and documents
    distances, indices = index.search(
        query_embedding,
        top_k
    )

    print("\nQuery :", query)
    print("-" * 60)

    for rank, (idx, distance) in enumerate(
        zip(indices[0], distances[0]),
        start=1
    ):
        print(f"{rank}. Distance = {distance:.4f}")

        # Index into documents to find the original document
        print(documents[idx])
        print()

# -------------------------------------------------------
# Test Queries
# -------------------------------------------------------
semantic_search("What is artificial intelligence?")

semantic_search("Tell me about Python programming")

semantic_search("Which library performs vector similarity search?")
