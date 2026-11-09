import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")

import json
import os
import shutil
import sys
import cohere
from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_openai import ChatOpenAI

load_dotenv(override=True)
sys.stdout.reconfigure(encoding="utf-8")

# =====================================================================
# Reranking: a first-pass retriever (keyword search, a cheap embedding
# model, whatever) is tuned for recall, not precision - it returns
# plausible candidates in a rough order. A reranker is a cross-encoder:
# it looks at the query and each FULL candidate together (instead of
# comparing two separate embeddings), which is slower but far more
# accurate - so it only runs on the small candidate list a retriever
# already narrowed things down to, not the whole corpus.
#
# Knowledge base: 50 insurance policy statements covering health, motor,
# life, travel, and home insurance claims. Health insurance is the
# target domain for the two questions below - the other lines are real
# distractors, not filler: "claim", "waiting period", and "premium"
# appear across every insurance type, so an embedding retriever tuned
# for recall genuinely pulls in wrong-domain matches for the reranker
# to filter back out.
# =====================================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PERSIST_DIR = os.path.join(BASE_DIR, "rerank_chroma_db")
shutil.rmtree(PERSIST_DIR, ignore_errors=True)

with open(os.path.join(BASE_DIR, "policy_documents.json"), encoding="utf-8") as f:
    POLICY_DOCUMENTS = json.load(f)

vectorstore = Chroma(
    collection_name="policy_docs",
    embedding_function=HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2"),
    persist_directory=PERSIST_DIR,
)
vectorstore.add_texts(POLICY_DOCUMENTS)

co = cohere.ClientV2(api_key=os.getenv("COHERE_API_KEY"))
answer_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

QUESTIONS = [
    "What documents are required to file a cashless health insurance claim at a network "
    "hospital, and within what time should hospitalization be intimated to the insurer?",

    "Is a pre-existing disease covered immediately under a new health insurance policy, and "
    "what happens to my coverage if I miss paying my premium on the due date?",
]


def answer_from(label: str, question: str, docs: list[str]) -> None:
    context = "\n".join(f"- {d}" for d in docs)
    prompt = (
        f"Answer the question using ONLY the context below. Be concise.\n\n"
        f"Context:\n{context}\n\nQuestion: {question}"
    )
    response = answer_llm.invoke(prompt)
    print(f"\n{label} ANSWER:\n  {response.content}")


for question in QUESTIONS:
    print("\n" + "=" * 70)
    print(f"QUESTION: {question}")
    print("=" * 70)

    # -----------------------------
    # BEFORE: a real recall-oriented retriever - plain embedding
    # similarity search against the whole 50-document KB, k=10.
    # -----------------------------
    retrieved = vectorstore.similarity_search_with_score(question, k=10)
    candidates = [doc.page_content for doc, _ in retrieved]

    print("\nBEFORE (naive retrieval order, top 10 by embedding distance):")
    for i, (doc, score) in enumerate(retrieved, start=1):
        print(f"  [{i}] distance={score:.4f}  {doc.page_content}")

    # -----------------------------
    # AFTER: rerank those same 10 candidates with a cross-encoder and
    # keep only the top 3 by true relevance.
    # -----------------------------
    results = co.rerank(
        model="rerank-v4.0-pro",
        query=question,
        documents=candidates,
        top_n=3,
    )

    print("\nAFTER (Cohere rerank, top 3 by true relevance):")
    reranked_docs = []
    for rank, result in enumerate(results.results, start=1):
        doc = candidates[result.index]
        reranked_docs.append(doc)
        print(f"  [{rank}] score={result.relevance_score:.3f}  {doc}")

    # -----------------------------
    # Payoff: the reordering isn't cosmetic - it changes what context
    # the LLM answers from. Compare the top-3 naive context against the
    # top-3 reranked context.
    # -----------------------------
    naive_top3 = candidates[:3]
    answer_from("BEFORE (naive top-3 context)", question, naive_top3)
    answer_from("AFTER (reranked top-3 context)", question, reranked_docs)
