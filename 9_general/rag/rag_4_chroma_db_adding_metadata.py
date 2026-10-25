import chromadb
from chromadb.utils import embedding_functions
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Initialize Chroma with persistence
client = chromadb.PersistentClient(path=os.path.join(BASE_DIR, "chromadb"))

# Hugging Face embedding function
embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)

# Create / load collection with embedding function
collection = client.get_or_create_collection(
    name="my_collection_hf_with_metadata",
    embedding_function=embedding_fn
)

# Knowledge base (Question -> Answer + Metadata)
knowledge_base = {
    "What is your shipping time?": {
        "answer": "Our standard shipping time is 3-5 business days.",
        "metadata": {"category": "shipping", "priority": "high"}
    },
    "What is your return policy?": {
        "answer": "You can return any product within 30 days of delivery.",
        "metadata": {"category": "returns", "priority": "medium"}
    },
    "What warranty do you provide?": {
        "answer": "All products come with a one-year warranty covering manufacturing defects.",
        "metadata": {"category": "warranty", "priority": "medium"}
    },
    "What payment methods do you accept?": {
        "answer": "We accept credit cards, debit cards, and PayPal.",
        "metadata": {"category": "payment", "priority": "low"}
    },
    "How can I contact customer support?": {
        "answer": "You can reach our support team 24/7 via email or chat.",
        "metadata": {"category": "support", "priority": "high"}
    }
}

# Prepare metadata (add answer to the existing metadata)
metadatas = []

for item in knowledge_base.values():
    md = item["metadata"].copy()
    md["answer"] = item["answer"]
    metadatas.append(md)

# Add data with metadata
collection.add(
    documents=list(knowledge_base.keys()),   # Embed the QUESTIONS
    ids=[str(i) for i in range(len(knowledge_base))],
    metadatas=metadatas
)

# Query ChromaDB using HF embeddings
user_input = "delivery lag"

results = collection.query(
    query_texts=[user_input],
    n_results=2
)

print("User Question:", user_input)
print()

for i in range(len(results["ids"][0])):
    print(f"Match {i+1}")
    print("Question :", results["documents"][0][i])
    print("Answer   :", results["metadatas"][0][i]["answer"])
    print("Category :", results["metadatas"][0][i]["category"])
    print("Priority :", results["metadatas"][0][i]["priority"])
    print("Distance :", results["distances"][0][i])
    print()

# Same search, but only among questions tagged category="returns".
# "where" filters on metadata first; similarity then ranks what is left.
results = collection.query(
    query_texts=[user_input],
    n_results=1,
    where={"category": "returns"}
)

print("Filtered to category = returns:")
print("Question :", results["documents"][0][0])
print("Answer   :", results["metadatas"][0][0]["answer"])
