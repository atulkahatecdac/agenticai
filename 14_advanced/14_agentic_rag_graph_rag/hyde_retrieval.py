import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")

import os
import shutil
import sys
from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_openai import ChatOpenAI

load_dotenv(override=True)
sys.stdout.reconfigure(encoding="utf-8")

# =====================================================================
# HyDE (Hypothetical Document Embeddings): a short, informally-phrased
# question often sits far away in embedding space from the formal,
# jargon-heavy passage that actually answers it - the two just don't use
# the same words. HyDE closes that gap by asking an LLM to draft a fake
# ANSWER to the question first (it doesn't have to be correct - it just
# has to sound like the corpus), then embeds and searches with THAT
# hypothetical document instead of the raw question. Retrieval becomes a
# document-to-document match instead of a question-to-document match.
# =====================================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PERSIST_DIR = os.path.join(BASE_DIR, "hyde_chroma_db")
shutil.rmtree(PERSIST_DIR, ignore_errors=True)

KB_DOCUMENTS = [
    "LangGraph is a library for building stateful, multi-actor applications with LLMs, "
    "built on top of LangChain.",
    "LangGraph models an agent's workflow as a graph of nodes and edges, where nodes are "
    "functions and edges define control flow.",
    "LangGraph supports conditional edges, which let the graph branch to different nodes "
    "based on the current state, similar to an if/else in ordinary code.",
    "LangGraph provides checkpointers such as MemorySaver and SqliteSaver to persist graph "
    "state across runs, which enables human-in-the-loop workflows and time travel.",
    "A LangGraph StateGraph must be compiled into a runnable app with the .compile() method "
    "before it can be invoked or streamed.",
]

vectorstore = Chroma(
    collection_name="langgraph_docs",
    embedding_function=HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2"),
    persist_directory=PERSIST_DIR,
)
vectorstore.add_texts(KB_DOCUMENTS)

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

question = "Can I pause my agent mid-way, let a human approve something, and later redo an earlier step if I need to?"


def show(label: str, results) -> None:
    print(f"\n{label}")
    for doc, score in results:
        print(f"  distance={score:.4f}  {doc.page_content}")


print(f"QUESTION: {question}")

# -----------------------------
# BEFORE: embed the question as-is. Chroma's score here is a distance -
# lower means more similar.
# -----------------------------
direct_results = vectorstore.similarity_search_with_score(question, k=3)
show("BEFORE (direct question embedding):", direct_results)

# -----------------------------
# HyDE: draft a hypothetical passage that WOULD answer the question, in
# the same documentation style as the corpus - then embed and search
# with that instead.
# -----------------------------
hyde_prompt = (
    "Write one short, confident sentence of technical documentation that would answer "
    f"this question, in the style of official framework docs. Do not hedge or mention "
    f"that it's hypothetical.\n\nQuestion: {question}"
)
hypothetical_doc = llm.invoke(hyde_prompt).content
print(f"\nHYPOTHETICAL DOCUMENT: {hypothetical_doc}")

hyde_results = vectorstore.similarity_search_with_score(hypothetical_doc, k=3)
show("AFTER (HyDE - embedding the hypothetical document):", hyde_results)
