# pip install chromadb
# Create a chroma client
# It is ephemeral - starts a Chroma server in memory
# Data will be deleted when the program ends
import chromadb
chroma_client = chromadb.Client()

# Create a collection
collection = chroma_client.create_collection(name="my_collection")
# We can also add a specific distance metric to be used
# collection = chroma_client.create_collection(
#     name="my_collection", 
#     distance_metric="cosine") # default
# Other options for distance: l2 (euclidean distance)
# and ip (inner product)

# Add some text to the collection
# Chroma will embed the text on its own using its own model
collection.add(
    ids=["id1", "id2", "id3", "id4", "id5"],
    documents=[
        "This is a document about agentic ai",
        "This is a document about global warming",
        "We are talking about classification algorithms",
        "Accounts and Bookkeeping",
        "Trial Balance and Balance Sheet."
    ]
)

# print the original documents and their corresponding vectors
# include=["documents","embeddings"] ensures numeric vectors are returned
data = collection.get(
    ids=["id1", "id2"],
    include=["documents", "embeddings"]
)

# Print document and its embedding vector
for doc_id, doc, emb in zip(data["ids"], data["documents"], data["embeddings"]):
    print("\nID:", doc_id)
    print("Document:", doc)
    print("Embedding vector (numeric):")
    print(emb)
    print("Vector length:", len(emb))

# Query the collection
results = collection.query(
    #query_texts=["How many calories does an apple have?"], # Chroma will embed this for you
    query_texts=["balance sheet"],
    n_results=2, # how many results to return
    include=["documents","distances","embeddings"]
)

print("\nQuery results:")
print(results)

