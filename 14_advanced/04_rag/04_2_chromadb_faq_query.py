# Step 2 of the help-desk FAQ example (deck: "When a Customer Asks a Question" and
# "How ChromaDB Finds the Best Match"). Run 04_1_chromadb_faq_store.py first.
#
#   - Embeds the customer's question with the SAME default model
#   - ChromaDB searches its HNSW index for the nearest stored questions
#   - The best match's answer comes back from metadata - no LLM needed
#
# Distances are squared L2: lower = closer. Try your own question at the prompt.
import os
import sys

import chromadb

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

client = chromadb.PersistentClient(path=os.path.join(BASE_DIR, "chroma_db"))
try:
    faq = client.get_collection("faq")
except Exception:
    sys.exit("No 'faq' collection yet - run 04_1_chromadb_faq_store.py first.")


def ask(question: str, show_ranking: bool = True) -> str:
    hits = faq.query(
        query_texts=[question],
        n_results=faq.count(),            # rank every entry, just to show the distances
        include=["documents", "metadatas", "distances"],
    )
    questions, metas, distances = hits["documents"][0], hits["metadatas"][0], hits["distances"][0]

    print(f'\nCustomer: "{question}"')
    if show_ranking:
        print("  Stored question                        Distance")
        for q, d in zip(questions, distances):
            print(f"  {q:<38} {d:.2f}")
    print(f'Best match: "{questions[0]}"')
    print(f"Reply:      {metas[0]['answer']}")
    return metas[0]["answer"]


# Shares almost no words with "When will my order arrive?" - but means the same
ask("My parcel hasn't come yet - where is it?")

# Narrow the search with a metadata filter before ranking
hits = faq.query(query_texts=["Can I get my money back?"], n_results=1, where={"category": "returns"})
print(f'\nWith where={{"category": "returns"}}: "{hits["documents"][0][0]}" -> {hits["metadatas"][0][0]["answer"]}')

# Your turn (press Enter to quit)
while True:
    try:
        q = input("\nAsk the help desk (Enter to quit): ").strip()
    except EOFError:
        break
    if not q:
        break
    ask(q, show_ranking=False)
