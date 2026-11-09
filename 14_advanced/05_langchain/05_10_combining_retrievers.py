import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

import os
import sys
import sqlite3
from typing import List
from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_community.document_loaders import PyPDFLoader, NotionDirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.retrievers import EnsembleRetriever

load_dotenv(override=True)

# LLM/doc text can contain characters outside Windows' default console
# codepage (cp1252) - reconfigure stdout to UTF-8 so printing doesn't crash.
sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

# =====================================================================
# Question: "Explain the employee reimbursement process."
# No single source below can answer this alone:
#   - the PDF has the RULES (deadlines, thresholds, what's non-reimbursable)
#   - the wiki has the PROCESS (who does what, in what order, in what system)
#   - the database has the current DOLLAR LIMITS per category (nothing
#     about limits is in either document - it's live, structured data)
# A complete answer genuinely needs all three combined.
# =====================================================================

QUESTION = "Explain the employee reimbursement process."

# ---------------------------------------------------------------------
# Source 1: Expense Policy PDF (vector retriever)
# Reused from 6_mcp/mcp_agentic_rag/data - a real synthetic company policy
# doc already used elsewhere in this repo.
# ---------------------------------------------------------------------
pdf_path = os.path.join(BASE_DIR, "..", "..", "6_mcp", "mcp_agentic_rag", "data", "Expense Policy.pdf")
policy_pages = PyPDFLoader(pdf_path).load()
policy_chunks = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50).split_documents(policy_pages)
policy_retriever = FAISS.from_documents(policy_chunks, embeddings).as_retriever(search_kwargs={"k": 2})
print(f"Policy retriever: {len(policy_chunks)} chunk(s) from Expense Policy.pdf")

# ---------------------------------------------------------------------
# Source 2: Internal wiki page (vector retriever)
# Same NotionDirectoryLoader pattern as 05_5_document_loaders.py - a directory
# of exported markdown pages.
# ---------------------------------------------------------------------
wiki_path = os.path.join(BASE_DIR, "reimbursement_wiki")
wiki_docs = NotionDirectoryLoader(wiki_path).load()
wiki_retriever = FAISS.from_documents(wiki_docs, embeddings).as_retriever(search_kwargs={"k": 2})
print(f"Wiki retriever: {len(wiki_docs)} document(s) from reimbursement_wiki/")

# ---------------------------------------------------------------------
# Source 3: reimbursement limits database (CUSTOM retriever)
# A retriever doesn't have to wrap a vector store at all - it just has to
# turn a query into a list of Documents. This one queries a plain SQLite
# table of current per-category limits instead of doing any embedding
# search, and still plugs into EnsembleRetriever exactly like the two
# vector-backed retrievers above.
# ---------------------------------------------------------------------
DB_PATH = os.path.join(BASE_DIR, "reimbursement_limits.db")

def init_limits_db() -> None:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("CREATE TABLE IF NOT EXISTS limits (category TEXT, details TEXT)")
    if conn.execute("SELECT COUNT(*) FROM limits").fetchone()[0] == 0:
        conn.executemany(
            "INSERT INTO limits (category, details) VALUES (?, ?)",
            [
                ("Meals", "Meals: $60/day domestic, $80/day international"),
                ("Hotel", "Hotel: $200/night standard cities, $350/night major metro cities"),
                ("Mileage", "Mileage: $0.67 per mile for personal vehicle use"),
                ("Airfare", "Airfare: economy class required under 6 hours; business class allowed over 6 hours with VP approval"),
                ("Client Entertainment", "Client Entertainment: $100 per person per event"),
            ],
        )
        conn.commit()
    conn.close()

init_limits_db()

class ReimbursementLimitsRetriever(BaseRetriever):
    """Custom retriever over a SQLite table instead of a vector store.

    Falls back to returning every category when the query doesn't name a
    specific one - a broad question like "explain the process" needs the
    full limits picture, not just one row.
    """

    def _get_relevant_documents(
        self, query: str, *, run_manager: CallbackManagerForRetrieverRun
    ) -> List[Document]:
        conn = sqlite3.connect(DB_PATH)
        rows = conn.execute("SELECT category, details FROM limits").fetchall()
        conn.close()

        query_lower = query.lower()
        matches = [(cat, details) for cat, details in rows if cat.lower() in query_lower]
        selected = matches if matches else rows

        return [
            Document(page_content=details, metadata={"source": "reimbursement_limits.db", "category": cat})
            for cat, details in selected
        ]

limits_retriever = ReimbursementLimitsRetriever()
print("Limits retriever: querying reimbursement_limits.db\n")

# =====================================================================
# EnsembleRetriever - merges all three via Reciprocal Rank Fusion,
# regardless of the fact that one of them isn't vector-based at all.
# =====================================================================
ensemble_retriever = EnsembleRetriever(
    retrievers=[policy_retriever, wiki_retriever, limits_retriever],
    weights=[1 / 3, 1 / 3, 1 / 3],
)

def preview_of(doc: Document) -> str:
    source = os.path.basename(str(doc.metadata.get("source", "?")))
    text = doc.page_content.strip().replace("\n", " ")[:110]
    return f"source={source}  \"{text}...\""

print(f"{'=' * 70}")
print(f"Query: {QUESTION!r}")
print("=" * 70)

print("\nPolicy PDF retriever alone:")
for doc in policy_retriever.invoke(QUESTION):
    print(f"  - {preview_of(doc)}")

print("\nWiki retriever alone:")
for doc in wiki_retriever.invoke(QUESTION):
    print(f"  - {preview_of(doc)}")

print("\nLimits DB retriever alone:")
for doc in limits_retriever.invoke(QUESTION):
    print(f"  - {preview_of(doc)}")

print("\nEnsemble (all three, merged via RRF):")
for i, doc in enumerate(ensemble_retriever.invoke(QUESTION), start=1):
    print(f"  [{i}] {preview_of(doc)}")
