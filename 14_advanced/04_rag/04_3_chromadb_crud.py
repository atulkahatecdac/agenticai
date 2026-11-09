import chromadb
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Create (or open) a persistent ChromaDB database
client = chromadb.PersistentClient(path=os.path.join(BASE_DIR, "chroma_db"))
collection = client.get_or_create_collection("crud_demo")

# Start from a clean collection so the demo is repeatable
try:
    collection.delete(ids=collection.get()["ids"])
except Exception:
    pass


# -------------------------------------------------
# Create
# -------------------------------------------------
documents = [
    "Python is a popular programming language for AI and data science.",
    "Machine learning enables computers to learn from data.",
    "ChromaDB is a vector database used in Retrieval-Augmented Generation (RAG).",
]
ids = [str(i) for i in range(1, len(documents) + 1)]
metadatas = [{"topic": "programming"}, {"topic": "ai"}, {"topic": "database"}]

collection.add(ids=ids, documents=documents, metadatas=metadatas)
print(f"Created {len(documents)} documents.\n")


# -------------------------------------------------
# Read
# -------------------------------------------------
result = collection.get(ids=["2"])
print("Read by id '2':")
print(f"  Document: {result['documents'][0]}")
print(f"  Metadata: {result['metadatas'][0]}\n")

query = "database for storing vectors"
search_results = collection.query(query_texts=[query], n_results=2)
print(f"Semantic search for {query!r}:")
for doc, distance in zip(search_results["documents"][0], search_results["distances"][0]):
    print(f"  ({distance:.4f}) {doc}")
print()


# -------------------------------------------------
# Update
# -------------------------------------------------
collection.update(
    ids=["2"],
    documents=["Machine learning enables computers to learn patterns from data without explicit programming."],
    metadatas=[{"topic": "ai", "updated": True}],
)
updated = collection.get(ids=["2"])
print("Updated document '2':")
print(f"  Document: {updated['documents'][0]}")
print(f"  Metadata: {updated['metadatas'][0]}\n")


# -------------------------------------------------
# Delete
# -------------------------------------------------
collection.delete(ids=["3"])
print("Deleted document '3'.")
print(f"Remaining document count: {collection.count()}")
