# Use a persistent ChromaDB
# Add our knowledge base to the collection
# Query the collection using semantic search
import chromadb

client = chromadb.PersistentClient(path=r"c:/code/agenticai/9_general/rag/chromadb")

collection = client.get_or_create_collection(name="my_collection")

knowledge_base = {
    "shipping_time": "Our standard shipping time is 3-5 business days.",
    "return_policy": "You can return any product within 30 days of delivery.",
    "warranty": "All products come with a one-year warranty covering manufacturing defects.",
    "payment_methods": "We accept credit cards, debit cards, and PayPal.",
    "customer_support": "You can reach our support team 24/7 via email or chat."
}

collection.add(
    documents=list(knowledge_base.keys()),              # Embed the QUESTIONS
    metadatas=[{"answer": a} for a in knowledge_base.values()],  # Store answers
    ids=[str(i) for i in range(len(knowledge_base))]
)

# User query
user_input = "I am not happy with the product"

results = collection.query(
    query_texts=[user_input],      # Chroma embeds this automatically
    n_results=1
)

matched_question = results["documents"][0][0]
answer = results["metadatas"][0][0]["answer"]

print("User Question :", user_input)
print("Matched FAQ   :", matched_question)
print("Answer        :", answer)