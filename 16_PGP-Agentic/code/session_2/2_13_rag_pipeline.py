import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

import os
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

load_dotenv(override=True)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PDF_PATH = os.path.join(BASE_DIR, "..", "..", "..", "9_general", "rag", "Principles-of-Data-Science.pdf")

# =====================================================================
# STAGE 1: LOADER
# Reads the raw source and turns it into a list of Document objects
# (page_content + metadata). Everything downstream only ever depends on
# this Document interface, regardless of what the loader was.
# =====================================================================
print("=" * 70)
print("STAGE 1: LOADER (PyPDFLoader)")
print("=" * 70)

pages = PyPDFLoader(PDF_PATH).load()
print(f"Loaded {len(pages)} page(s) from {os.path.basename(PDF_PATH)}")

# =====================================================================
# STAGE 2: SPLITTER
# A whole page is too big and too topically mixed to embed usefully as
# one vector, so break it into smaller, semantically coherent-ish chunks.
# RecursiveCharacterTextSplitter is the standard default: fast, no extra
# model needed, good enough for most corpora (see text_splitters.py for
# the SemanticChunker alternative when topic boundaries matter more).
# =====================================================================
print("\n" + "=" * 70)
print("STAGE 2: SPLITTER (RecursiveCharacterTextSplitter)")
print("=" * 70)

splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
chunks = splitter.split_documents(pages)
print(f"Split {len(pages)} page(s) into {len(chunks)} chunk(s)")

# =====================================================================
# STAGE 3: EMBEDDER
# Turns each chunk's text into a vector that captures its meaning.
# Local sentence-transformer model - no API calls, no quota, no cost.
# =====================================================================
print("\n" + "=" * 70)
print("STAGE 3: EMBEDDER (HuggingFaceEmbeddings)")
print("=" * 70)

embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
print("Loaded embedding model: all-MiniLM-L6-v2")

# =====================================================================
# STAGE 4: RETRIEVER
# Stores every chunk's embedding in a vector index (FAISS, in-memory
# here) and, given a query, returns the k chunks whose embeddings are
# closest to the query's embedding.
# =====================================================================
print("\n" + "=" * 70)
print("STAGE 4: RETRIEVER (FAISS)")
print("=" * 70)

vectorstore = FAISS.from_documents(chunks, embeddings)
retriever = vectorstore.as_retriever(search_kwargs={"k": 4})
print(f"Indexed {len(chunks)} chunk(s) into FAISS, retriever will return top 4 per query")

def format_docs(docs) -> str:
    return "\n\n".join(doc.page_content for doc in docs)

# =====================================================================
# STAGE 5: GENERATOR
# Takes the retrieved chunks + the original question and asks an LLM to
# synthesize a final answer grounded in that context - the "G" in RAG.
# Wired together with LCEL: the dict below runs "context" (retriever |
# format_docs) and "question" (RunnablePassthrough, i.e. pass the input
# straight through) IN PARALLEL, merges them into one dict, and feeds
# that into the prompt -> llm -> output parser.
# =====================================================================
print("\n" + "=" * 70)
print("STAGE 5: GENERATOR (OpenAI)")
print("=" * 70)

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)

prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        "Answer the question using only the context below, which is excerpted "
        "from the textbook 'Principles of Data Science'. If the answer isn't in "
        "the context, say you don't know instead of guessing.\n\nContext:\n{context}",
    ),
    ("human", "{question}"),
])

rag_chain = (
    {"context": retriever | format_docs, "question": RunnablePassthrough()}
    | prompt
    | llm
    | StrOutputParser()
)

# -----------------------------
# Run the full pipeline end to end
# -----------------------------
if __name__ == "__main__":
    question = "What is a p-value and how is it used in hypothesis testing?"

    print(f"\nQuestion: {question}")
    print("-" * 70)

    retrieved = retriever.invoke(question)
    for i, doc in enumerate(retrieved, start=1):
        preview = doc.page_content.strip().replace("\n", " ")[:120]
        print(f"  [{i}] page={doc.metadata.get('page_label')}  \"{preview}...\"")

    answer = rag_chain.invoke(question)
    print(f"\nAnswer:\n{answer}")
