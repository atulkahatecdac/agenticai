# Corrective RAG (CRAG): grade the retrieved documents, then pick a source.
#   all relevant  (CORRECT)   -> answer from the knowledge base only
#   some relevant (AMBIGUOUS) -> keep the relevant parts + add a web search
#   none relevant (INCORRECT) -> drop the KB, rewrite the query, web only
# "Refine" keeps only the sentences of the relevant documents that actually
# help - a document can be relevant overall and still contain noise.

import os
import sys
import json
import chromadb
from dotenv import load_dotenv
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from langchain_tavily import TavilySearch

load_dotenv(override=True)
sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(BASE_DIR, "policy_documents.json"), encoding="utf-8") as f:
    documents = json.load(f)

kb = chromadb.Client().create_collection("policy_docs")
kb.add(ids=[str(i) for i in range(len(documents))], documents=documents)

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
web = TavilySearch(max_results=3)


class Relevance(BaseModel):
    relevant: bool


class KeptSentences(BaseModel):
    sentences: list[str]


def is_relevant(question: str, doc: str) -> bool:
    return llm.with_structured_output(Relevance).invoke(
        f"Question: {question}\n\nDocument: {doc}\n\nDoes this document help answer the question?"
    ).relevant


def refine(question: str, docs: list[str]) -> list[str]:
    sentences = [s.strip() for d in docs for s in d.split(". ") if s.strip()]
    kept = llm.with_structured_output(KeptSentences).invoke(
        f"Question: {question}\n\nSentences:\n" + "\n".join(f"- {s}" for s in sentences)
        + "\n\nReturn, verbatim, only the sentences that directly help answer the question."
    ).sentences
    print(f"[refine] kept {len(kept)}/{len(sentences)} sentences")
    return kept


def web_search(question: str) -> list[str]:
    query = llm.invoke(f"Rewrite as a short keyword web search query. Reply with the query only:\n{question}").content
    results = web.invoke({"query": query}).get("results", [])
    print(f"[web search] '{query}' -> {len(results)} result(s)")
    return [r["content"] for r in results]


def corrective_rag(question: str) -> str:
    docs = kb.query(query_texts=[question], n_results=3)["documents"][0]
    relevant = [d for d in docs if is_relevant(question, d)]

    grade = "CORRECT" if len(relevant) == len(docs) else "AMBIGUOUS" if relevant else "INCORRECT"
    print(f"[grade] {len(relevant)}/{len(docs)} relevant -> {grade}")

    context = refine(question, relevant) if relevant else []
    if grade != "CORRECT":
        context += web_search(question)

    return llm.invoke(
        "Answer using ONLY the context. Be concise.\n\nContext:\n"
        + "\n".join(f"- {c}" for c in context) + f"\n\nQuestion: {question}"
    ).content


QUESTIONS = [
    # CORRECT: fully answerable from the knowledge base
    "What documents are required to file a cashless health insurance claim at a network "
    "hospital, and within what time should hospitalization be intimated to the insurer?",
    # AMBIGUOUS: the KB has the IRDAI 30-day rule, but not this year's settlement ratios
    "What is the current claim settlement ratio for health insurers in India this year, "
    "and how long does IRDAI require a claim to be settled once documents are submitted?",
    # INCORRECT: nothing in the KB covers new circulars
    "Has IRDAI issued any new circular on health insurance claim settlement timelines this year?",
]

for question in QUESTIONS:
    print("\n" + "=" * 70 + f"\nQUESTION: {question}\n" + "=" * 70)
    print(f"ANSWER: {corrective_rag(question)}")
