import warnings
warnings.filterwarnings("ignore")

import sys
from langchain.retrievers import ParentDocumentRetriever
from langchain.storage import InMemoryStore
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

sys.stdout.reconfigure(encoding="utf-8")

# =====================================================================
# Parent-child chunking: SEARCH small, RETURN big.
#
# Chunk size is a tug of war:
#   small chunks -> precise embeddings, but the answer's context is cut off
#   big chunks   -> full context, but one vector has to stand for many ideas
#
# ParentDocumentRetriever does both: it embeds small CHILD chunks for the
# search, keeps the full PARENT section in a document store, and returns
# the parent of whichever children matched.
#
# No LLM and no API key: this script only retrieves, so the result is the
# same every run.
# =====================================================================

SECTIONS = [
    ("4. Motor claims",
     "4.1 Report an accident to the insurer within 48 hours, by phone or in the app. "
     "4.2 The documents needed for a motor claim are: the claim form, a copy of the driving licence, "
     "the registration certificate, the police FIR if a third party was involved, and the repair estimate. "
     "4.3 A surveyor inspects the vehicle within 3 working days of the report. "
     "4.4 Submit the documents listed above within 7 days of the survey, or the claim may be closed."),
    ("5. Health claims",
     "5.1 For a planned admission, inform the insurer at least 48 hours before you are admitted. "
     "5.2 For an emergency admission, inform the insurer within 24 hours. "
     "5.3 Cashless treatment is available only at network hospitals; elsewhere you pay and claim back. "
     "5.4 Reimbursement claims must reach the insurer within 30 days of discharge."),
    ("6. Travel claims",
     "6.1 Report lost baggage to the airline before leaving the airport and get a property irregularity report. "
     "6.2 Flight-delay cover pays only for delays of more than 6 hours. "
     "6.3 Send all travel claims within 30 days of returning home, with boarding passes and receipts."),
]
parents = [Document(page_content=f"{title}\n{body}", metadata={"section": title}) for title, body in SECTIONS]

embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
child_splitter = RecursiveCharacterTextSplitter(
    chunk_size=160, chunk_overlap=0, separators=[". ", " "], keep_separator="end"
)

# ---------------------------------------------------------------------
# Small chunks only - the usual way.
# ---------------------------------------------------------------------
children = child_splitter.split_documents(parents)
small_only = Chroma.from_documents(children, embeddings, collection_name="small_only")

# ---------------------------------------------------------------------
# Parent-child: children in the vector store, parents in a doc store.
# ---------------------------------------------------------------------
parent_child = ParentDocumentRetriever(
    vectorstore=Chroma(collection_name="children", embedding_function=embeddings),
    docstore=InMemoryStore(),          # use a persistent store (e.g. Redis, SQL) in production
    child_splitter=child_splitter,
    search_kwargs={"k": 1},
)
parent_child.add_documents(parents)

print(f"{len(parents)} parent sections -> {len(children)} child chunks\n")

for question in [
    "Within how many days must I submit my motor claim documents, and which documents?",
    "How long after discharge can I send a reimbursement claim?",
]:
    print("=" * 76 + f"\nQ: {question}\n" + "=" * 76)
    hit = small_only.similarity_search(question, k=1)[0]
    print(f"SMALL CHUNK ({len(hit.page_content)} chars) - precise, but is everything you need in it?\n  {hit.page_content}\n")
    parent = parent_child.invoke(question)[0]
    print(f"PARENT-CHILD ({len(parent.page_content)} chars) - found by the same child, returns its whole section:")
    print("  " + parent.page_content.replace("\n", "\n  ") + "\n")

print("""What to notice
- Q1: the best child is clause 4.2, cut off in the middle of the document list - and the
  '7 days' is in 4.4, a different chunk. The parent section has both.
- Q2: the child alone is enough - parent-child costs more prompt tokens for no gain. Use it
  when chunks refer to each other (clauses, steps, tables), not for self-contained facts.
- Related: late chunking embeds the WHOLE document with a long-context embedding model first
  and splits the token vectors afterwards, so each chunk's vector already "knows" its context.""")
