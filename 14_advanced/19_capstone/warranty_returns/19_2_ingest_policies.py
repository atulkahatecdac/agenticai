# pip install chromadb pypdf rank_bm25
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

import glob
import os
import re
import sys

import chromadb
from pypdf import PdfReader
from rank_bm25 import BM25Okapi

from capstone_common import CHROMA_DIR, COLLECTION, POLICY_DIR, POLICY_VERSION

sys.stdout.reconfigure(encoding="utf-8")

# =====================================================================
# STEP 2 of the capstone: the RAG layer.
#
# The three design decisions from the slides, in code:
#   INDEX STRATEGY  one Chroma collection, with metadata on every chunk
#                   (doc_type, product_category, policy_version, section)
#   CHUNKING        one policy CLAUSE = one chunk, so a clause is never cut
#                   in half and can be cited as "Warranty_Policy 4.2"
#   RETRIEVAL       metadata filter first (product category), then HYBRID
#                   search: semantic (embeddings) + keyword (BM25), merged
#                   with Reciprocal Rank Fusion
#
# Embeddings are Chroma's built-in local model (all-MiniLM-L6-v2), so this
# step needs no API key.
#
# Run it:
#   python 19_2_ingest_policies.py                 build the index + demo queries
#   python 19_2_ingest_policies.py "your question" query the existing index
# =====================================================================

DOC_TYPES = {
    "Warranty_Policy": "warranty_policy",
    "Returns_Policy": "returns_policy",
    "Refund_and_Approval_Policy": "refund_policy",
}
# Heading keyword -> product_category. Clauses that match none apply to "all".
CATEGORY_KEYWORDS = [
    ("mobile phone", "mobile"), ("laptop", "laptop"), ("audio product", "audio"),
    ("small appliance", "appliance"), ("accessor", "accessory"),
]
CLAUSE_START = re.compile(r"(?m)^(\d+\.\d+)\s+")


def chunk_by_clause(pdf_path: str) -> list[dict]:
    """Split one policy PDF into clause-sized chunks with metadata."""
    doc_name = os.path.splitext(os.path.basename(pdf_path))[0]
    text = "\n".join(page.extract_text() for page in PdfReader(pdf_path).pages)
    starts = list(CLAUSE_START.finditer(text))
    chunks = []
    for i, match in enumerate(starts):
        end = starts[i + 1].start() if i + 1 < len(starts) else len(text)
        body = " ".join(text[match.start():end].split())     # undo PDF line wraps
        heading = body[len(match.group(1)):].split(". ")[0].strip().lower()   # "audio products - warranty period"
        category = next((cat for key, cat in CATEGORY_KEYWORDS if key in heading), "all")
        chunks.append({
            "id": f"{doc_name}:{match.group(1)}",
            "text": body,
            "metadata": {
                "doc_name": doc_name,
                "doc_type": DOC_TYPES.get(doc_name, "product_guide"),
                "product_category": category,
                "policy_version": POLICY_VERSION,
                "section": match.group(1),
            },
        })
    return chunks


def build_index() -> int:
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    try:
        client.delete_collection(COLLECTION)      # rebuild from scratch every time
    except Exception:
        pass
    collection = client.create_collection(COLLECTION)
    chunks = []
    for pdf in sorted(glob.glob(os.path.join(POLICY_DIR, "*.pdf"))):
        doc_chunks = chunk_by_clause(pdf)
        print(f"  {os.path.basename(pdf):<34} {len(doc_chunks):>2} clauses")
        chunks.extend(doc_chunks)
    collection.add(ids=[c["id"] for c in chunks],
                   documents=[c["text"] for c in chunks],
                   metadatas=[c["metadata"] for c in chunks])
    return len(chunks)


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def retrieve(query: str, product_category: str | None = None, doc_types: list[str] | None = None,
             k: int = 4) -> list[dict]:
    """Metadata filter -> semantic search + BM25 keyword search -> Reciprocal Rank Fusion.

    product_category keeps clauses for that category PLUS the clauses that apply to
    all products (exclusions, remedies, approvals) - never another category's.
    """
    collection = chromadb.PersistentClient(path=CHROMA_DIR).get_collection(COLLECTION)

    conditions = []
    if product_category and product_category != "all":
        conditions.append({"product_category": {"$in": [product_category, "all"]}})
    if doc_types:
        conditions.append({"doc_type": {"$in": doc_types}})
    where = None if not conditions else conditions[0] if len(conditions) == 1 else {"$and": conditions}

    # 1) Everything that survives the metadata filter is the candidate set
    candidates = collection.get(where=where, include=["documents", "metadatas"])
    ids = candidates["ids"]
    if not ids:
        return []
    docs = dict(zip(ids, candidates["documents"]))
    metas = dict(zip(ids, candidates["metadatas"]))

    # 2) Semantic ranking (embeddings)
    semantic = collection.query(query_texts=[query], n_results=min(len(ids), 10), where=where)["ids"][0]

    # 3) Keyword ranking (BM25) - catches exact words like "10 days" or "cracked"
    bm25 = BM25Okapi([_tokens(docs[i]) for i in ids])
    scores = bm25.get_scores(_tokens(query))
    keyword = [i for i, s in sorted(zip(ids, scores), key=lambda p: -p[1]) if s > 0][:10]

    # 4) Reciprocal Rank Fusion: a clause ranked well by BOTH lists wins
    fused: dict[str, float] = {}
    for ranking in (semantic, keyword):
        for rank, chunk_id in enumerate(ranking):
            fused[chunk_id] = fused.get(chunk_id, 0) + 1 / (60 + rank + 1)
    top = sorted(fused, key=fused.get, reverse=True)[:k]

    return [{"id": i, "text": docs[i], **metas[i],
             "citation": f"{metas[i]['doc_name'].replace('_', ' ')} clause {metas[i]['section']}",
             "in_semantic": i in semantic[:k], "in_keyword": i in keyword[:k]} for i in top]


def get_clause(doc_name: str, section: str) -> dict | None:
    """Fetch one known clause by its id (used when a rule needs an exact clause)."""
    collection = chromadb.PersistentClient(path=CHROMA_DIR).get_collection(COLLECTION)
    got = collection.get(ids=[f"{doc_name}:{section}"], include=["documents", "metadatas"])
    if not got["ids"]:
        return None
    meta = got["metadatas"][0]
    return {"id": got["ids"][0], "text": got["documents"][0], **meta,
            "citation": f"{doc_name.replace('_', ' ')} clause {section}"}


def show(query: str, product_category: str | None = None):
    print("\n" + "-" * 70)
    print(f"QUERY : {query}")
    print(f"FILTER: product_category in [{product_category}, all]" if product_category else "FILTER: none")
    for hit in retrieve(query, product_category):
        found_by = "+".join(n for n, f in (("semantic", hit["in_semantic"]), ("keyword", hit["in_keyword"])) if f)
        print(f"  [{hit['citation']}] ({hit['product_category']}, found by {found_by or 'fusion'})")
        print(f"      {hit['text'][:150]}...")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        show(" ".join(sys.argv[1:]))
        sys.exit()

    print("=" * 70)
    print("INGESTING POLICIES (one clause = one chunk)")
    print("=" * 70)
    total = build_index()
    print(f"Indexed {total} clauses into Chroma collection '{COLLECTION}' -> {CHROMA_DIR}")

    print("\nOne chunk, as stored:")
    sample = get_clause("Warranty_Policy", "4.2")
    print(f"  text    : {sample['text']}")
    print(f"  metadata: doc_type={sample['doc_type']}, product_category={sample['product_category']}, "
          f"policy_version={sample['policy_version']}, section={sample['section']}")

    # Same question, with and without the metadata filter - the filter is what
    # stops the laptop or mobile warranty clause from being returned for headphones.
    show("headphones not charging, bought 5 months ago, how long is the warranty")
    show("headphones not charging, bought 5 months ago, how long is the warranty", "audio")
    show("can I return it after 10 days", None)
    show("screen cracked after I dropped the phone", "mobile")
