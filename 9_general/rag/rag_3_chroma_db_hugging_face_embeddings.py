# pip install chromadb sentence-transformers
import chromadb
from chromadb.utils import embedding_functions

# Initialize Chroma with persistence
client = chromadb.PersistentClient(path=r"c:/code/agenticai/9_general/rag/chromadb")

# Hugging Face embedding function
# These are higher quality embeddings
embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)

# Create / load collection with embedding function
collection = client.get_or_create_collection(
    name="my_collection_hf",
    embedding_function=embedding_fn
)

# Knowledge base (Question -> Answer)
knowledge_base = {
    "What is your shipping time?":
        "Our standard shipping time is 3-5 business days.",

    "What is your return policy?":
        "You can return any product within 30 days of delivery.",

    "What warranty do you provide?":
        "All products come with a one-year warranty covering manufacturing defects.",

    "What payment methods do you accept?":
        "We accept credit cards, debit cards, and PayPal.",

    "How can I contact customer support?":
        "You can reach our support team 24/7 via email or chat."
}

# Add data
collection.add(
    documents=list(knowledge_base.keys()),                  # Embed the QUESTIONS
    metadatas=[{"answer": a} for a in knowledge_base.values()],  # Store answers
    ids=[str(i) for i in range(len(knowledge_base))]
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
    print("Distance :", results["distances"][0][i])
    print()