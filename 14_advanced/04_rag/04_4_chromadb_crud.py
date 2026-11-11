# CRUD and metadata filters on the full help-desk FAQ (deck: "ChromaDB: CRUD and
# Metadata Filters"). All 48 questions from faq.csv go into one collection, with
# the answer and category as metadata - the same layout as 04_1, just complete.
#
# No API key: ChromaDB's default local embedding model.
import csv
import os

import chromadb

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(BASE_DIR, "faq.csv"), encoding="utf-8") as f:
    FAQ = list(csv.DictReader(f))

client = chromadb.PersistentClient(path=os.path.join(BASE_DIR, "chroma_db"))
try:
    client.delete_collection("faq_all")   # start clean so the demo is repeatable
except Exception:
    pass
faq = client.create_collection("faq_all")

# -------------------------------------------------
# Create
# -------------------------------------------------
faq.add(
    ids=[row["id"] for row in FAQ],
    documents=[row["question"] for row in FAQ],
    metadatas=[{"answer": row["answer"], "category": row["category"]} for row in FAQ],
)
print(f"Created: {faq.count()} FAQ entries\n")

# -------------------------------------------------
# Read - by id, and by metadata (no similarity involved)
# -------------------------------------------------
entry = faq.get(ids=["9"])
print(f"Read id 9:  {entry['documents'][0]}  ->  {entry['metadatas'][0]['answer']}")

payments = faq.get(where={"category": "payments"})
print(f"Read where category = payments: {len(payments['ids'])} entries")

# where_document filters on the stored text itself
otp = faq.get(where_document={"$contains": "OTP"})
print(f"Read where the question contains 'OTP': {otp['documents']}\n")

# -------------------------------------------------
# Search by meaning, narrowed by metadata
# An ambiguous question: delivery time or refund time? A help widget on the
# Returns page already knows the context, so it passes a where filter.
# -------------------------------------------------
question = "How long does it take?"
for where in (None, {"category": "returns"}):
    hits = faq.query(query_texts=[question], n_results=3, where=where)
    print(f'Query "{question}"  where={where}')
    for q, d in zip(hits["documents"][0], hits["distances"][0]):
        print(f"   {d:5.2f}  {q}")
print()

# -------------------------------------------------
# Update - the shop raises its free-delivery threshold
# -------------------------------------------------
faq.update(
    ids=["9"],
    metadatas=[{"answer": "Delivery is free on orders above Rs 599; below that it costs Rs 40.", "category": "shipping"}],
)
print(f"Updated id 9:  {faq.get(ids=['9'])['metadatas'][0]['answer']}")

# -------------------------------------------------
# Delete - the shop stops price matching questions
# -------------------------------------------------
faq.delete(ids=["47"])
print(f"Deleted id 47; {faq.count()} entries left")
