# pip install openai-agents chromadb pypdf
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

import asyncio
import json
import os
import re
import sys

import chromadb
from agents import Agent, Runner, function_tool
from pypdf import PdfReader

from common import CHROMA_DIR, COLLECTION, DOCS_DIR, MODEL, CustomerSession, load_step, print_trace

sys.stdout.reconfigure(encoding="utf-8")

# =====================================================================
# STEP 4: RAG - the "policy documents, FAQs" box in the diagram.
#
# Facts about ONE customer live in databases (steps 3 and 5). Rules that
# apply to EVERYONE ("is maternity covered?", "what is the waiting
# period?") live in documents. RAG = find the right passage, then let the
# LLM answer from it.
#
#   INGEST   PDF -> text -> one CLAUSE per chunk (so a clause is never cut
#            in half and can be cited as "clause 3.4") -> ChromaDB, with
#            metadata on every chunk: policy_type, doc_type, doc_name, section
#   SEARCH   embed the question, return the closest chunks.
#            The tool ALWAYS filters policy_type = "health": this assistant
#            only supports health, and the filter is in code, so the LLM
#            cannot forget it.
#
# Embeddings are ChromaDB's built-in local model (all-MiniLM-L6-v2), so
# building the index needs no API key.
#
# Run it:
#   python 4_rag_policy_docs.py                  build the index + retrieval demo + agent demo
#   python 4_rag_policy_docs.py "your question"  search the existing index (no LLM)
# =====================================================================

CLAUSE_START = re.compile(r"(?m)^(\d+\.\d+)\s+")


def chunk_by_clause(pdf_path: str, policy_type: str, doc_type: str) -> list[dict]:
    doc_name = os.path.splitext(os.path.basename(pdf_path))[0]
    text = "\n".join(page.extract_text() for page in PdfReader(pdf_path).pages)
    starts = list(CLAUSE_START.finditer(text))
    chunks = []
    for i, match in enumerate(starts):
        end = starts[i + 1].start() if i + 1 < len(starts) else len(text)
        chunks.append({
            "id": f"{doc_name}:{match.group(1)}",
            "text": " ".join(text[match.start():end].split()),      # undo PDF line wraps
            "metadata": {"doc_name": doc_name, "policy_type": policy_type,
                         "doc_type": doc_type, "section": match.group(1)},
        })
    return chunks


def build_index() -> list[dict]:
    with open(os.path.join(DOCS_DIR, "doc_index.json"), encoding="utf-8") as f:
        doc_index = json.load(f)
    chunks = []
    for doc in doc_index:
        chunks += chunk_by_clause(os.path.join(DOCS_DIR, doc["file"]), doc["policy_type"], doc["doc_type"])
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    try:
        client.delete_collection(COLLECTION)          # rebuild from scratch every time
    except Exception:
        pass
    collection = client.create_collection(COLLECTION)
    collection.add(ids=[c["id"] for c in chunks], documents=[c["text"] for c in chunks],
                   metadatas=[c["metadata"] for c in chunks])
    return chunks


_collection = None


def search_docs(query: str, policy_type: str | None = "health", k: int = 4) -> list[dict]:
    """Plain function: also used by the MCP server in step 7. policy_type=None searches everything."""
    global _collection
    if _collection is None:
        _collection = chromadb.PersistentClient(path=CHROMA_DIR).get_collection(COLLECTION)
    where = {"policy_type": policy_type} if policy_type else None
    res = _collection.query(query_texts=[query], n_results=k, where=where)
    return [{"citation": f"{m['doc_name']} clause {m['section']}", "policy_type": m["policy_type"],
             "text": doc, "distance": round(d, 3)}
            for doc, m, d in zip(res["documents"][0], res["metadatas"][0], res["distances"][0])]


def format_hits(hits: list[dict]) -> str:
    return "\n".join(f"[{h['citation']}] {h['text']}" for h in hits)


@function_tool
def search_policy_docs(query: str) -> str:
    """Search the SecureLife HEALTH policy wording and FAQs. Use for questions about what is
    covered or excluded, waiting periods, limits, claim procedures, renewal and bonuses.
    Each result starts with its citation, e.g. [Health_Policy_Wording clause 3.4].

    Args:
        query: the customer's question, rephrased as a search query.
    """
    return format_hits(search_docs(query, policy_type="health"))


def show(title: str, hits: list[dict]) -> None:
    print(f"\n  {title}")
    for h in hits:
        print(f"    {h['distance']:.3f}  [{h['policy_type']:<6}] {h['citation']:<36} {h['text'][:70]}...")


async def main() -> None:
    if len(sys.argv) > 1:
        show(f"Search: {' '.join(sys.argv[1:])}", search_docs(" ".join(sys.argv[1:])))
        return

    chunks = build_index()
    print(f"Indexed {len(chunks)} clause-chunks into ChromaDB collection '{COLLECTION}'.")
    print("\nOne chunk, as stored:")
    sample = next(c for c in chunks if c["id"] == "Health_Policy_Wording:3.4")
    print(f"  id       {sample['id']}\n  metadata {sample['metadata']}\n  text     {sample['text'][:110]}...")

    print("\nWHY THE FILTER MATTERS - same question, with and without policy_type = 'health'")
    q = "What is the waiting period?"
    show(f"'{q}'  WITHOUT filter  (other products leak in):", search_docs(q, policy_type=None))
    show(f"'{q}'  WITH health filter:", search_docs(q))

    print("\n\nNow the agent, with the SQL tool from step 3 AND this RAG tool:\n")
    sql = load_step("3_tool_sql.py")
    agent = Agent[CustomerSession](
        name="Insurance Assistant (SQL + RAG)",
        model=MODEL,
        instructions=lambda ctx, a: sql.instructions(ctx, a) +
            " When you use the policy documents, cite the clause, e.g. (Health_Policy_Wording clause 3.4).",
        tools=[sql.get_my_policies, search_policy_docs],
    )
    for question in ["Is maternity covered, and is there a waiting period?",
                     "Does my policy cover a hair transplant?"]:
        print(f"CUSTOMER: {question}")
        result = await Runner.run(agent, question, context=CustomerSession())
        print_trace(result)
        print()
    print("-> Rules come from documents, with a citation. Still missing: the customer's coverage")
    print("   amount and status - those live in the Insurance API (step 5).")


if __name__ == "__main__":
    asyncio.run(main())
