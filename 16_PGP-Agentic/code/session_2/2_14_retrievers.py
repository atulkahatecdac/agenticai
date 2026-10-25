import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

import os
import logging
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_openai import ChatOpenAI
from langchain.retrievers import MultiQueryRetriever, ContextualCompressionRetriever
from langchain.retrievers.document_compressors import LLMChainExtractor

load_dotenv(override=True)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PDF_PATH = os.path.join(BASE_DIR, "..", "..", "..", "9_general", "rag", "Principles-of-Data-Science.pdf")

# -----------------------------
# Shared setup: same load -> split -> embed -> index pipeline as
# rag_pipeline.py. Every retriever below wraps the SAME underlying FAISS
# index - what differs is how each one turns a query into final documents.
# -----------------------------
pages = PyPDFLoader(PDF_PATH).load()
chunks = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150).split_documents(pages)
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
vectorstore = FAISS.from_documents(chunks, embeddings)
print(f"Indexed {len(chunks)} chunks from {os.path.basename(PDF_PATH)}\n")

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

def show(label: str, docs) -> None:
    print(f"\n{'=' * 70}")
    print(f"{label} - {len(docs)} document(s)")
    print("=" * 70)
    for i, doc in enumerate(docs, start=1):
        preview = doc.page_content.strip().replace("\n", " ")[:150]
        print(f"  [{i}] ({len(doc.page_content)} chars) \"{preview}...\"")

# =====================================================================
# 1. VectorStoreRetriever
# The baseline: embed the query as-is, return the k nearest chunks by
# vector similarity. Fast, no extra LLM calls - but only as good as how
# closely the query's WORDING matches the documents' wording.
# =====================================================================
vector_retriever = vectorstore.as_retriever(search_kwargs={"k": 4})

query = "how do you know if your test result matters or is just luck?"
show(
    f"1. VectorStoreRetriever - query: {query!r}",
    vector_retriever.invoke(query),
)

# =====================================================================
# 2. MultiQueryRetriever
# The query above is informal and shares almost no vocabulary with the
# textbook's phrasing ("p-value", "statistical significance", "null
# hypothesis"). MultiQueryRetriever asks an LLM to generate several
# alternative phrasings of the SAME question, runs the base retriever for
# each one, and returns the union of unique documents - covering
# vocabulary the original query embedding alone would miss.
# Set logging to INFO to see the actual generated queries.
# =====================================================================
logging.basicConfig()
logging.getLogger("langchain.retrievers.multi_query").setLevel(logging.INFO)

multi_query_retriever = MultiQueryRetriever.from_llm(retriever=vector_retriever, llm=llm)
show(
    f"2. MultiQueryRetriever - query: {query!r}",
    multi_query_retriever.invoke(query),
)

# =====================================================================
# 3. ContextualCompressionRetriever
# Retrieval decides WHICH chunks come back; compression decides how much
# of EACH chunk is worth keeping. LLMChainExtractor asks the LLM to pull
# only the sentences relevant to the query out of each retrieved chunk,
# discarding the rest - same documents, less noise per document.
# =====================================================================
compressor = LLMChainExtractor.from_llm(llm)
compression_retriever = ContextualCompressionRetriever(
    base_compressor=compressor,
    base_retriever=vector_retriever,
)

question = "What is a p-value?"
plain_docs = vector_retriever.invoke(question)
compressed_docs = compression_retriever.invoke(question)

print(f"\n{'=' * 70}")
print(f"3. ContextualCompressionRetriever - query: {question!r}")
print("=" * 70)
for i, (plain, compressed) in enumerate(zip(plain_docs, compressed_docs), start=1):
    print(f"\n  [{i}] Before: {len(plain.page_content)} chars")
    print(f"      After:  {len(compressed.page_content)} chars")
    preview = compressed.page_content.strip().replace("\n", " ")[:200]
    print(f"      Kept: \"{preview}...\"")
