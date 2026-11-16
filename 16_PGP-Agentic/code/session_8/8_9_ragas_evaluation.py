# RAGAS: score a RAG pipeline with an LLM judge instead of eyeballing it,
# so changes (retriever, prompt, top-k) can be compared with numbers.
#   Faithfulness      - is every claim in the answer backed by the context?
#   Answer relevancy  - does the answer address the question asked?
#   Context recall    - did retrieval find what the reference answer needs?
#   Context precision - how much of what was retrieved was actually useful?

import os
import sys
import json
import chromadb
from dotenv import load_dotenv
from openai import AsyncOpenAI, OpenAI
from ragas.llms import llm_factory
from ragas.embeddings import HuggingFaceEmbeddings
from ragas.metrics.collections import AnswerRelevancy, ContextPrecisionWithoutReference, ContextRecall, Faithfulness

load_dotenv(override=True)
sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(BASE_DIR, "policy_documents.json"), encoding="utf-8") as f:
    documents = json.load(f)

kb = chromadb.Client().create_collection("policy_docs")
kb.add(ids=[str(i) for i in range(len(documents))], documents=documents)

client = OpenAI()

# ragas calls the judge LLM asynchronously, so it needs an AsyncOpenAI client
judge = llm_factory(model="gpt-4o-mini", provider="openai", client=AsyncOpenAI())
faithfulness = Faithfulness(llm=judge)
answer_relevancy = AnswerRelevancy(llm=judge, embeddings=HuggingFaceEmbeddings(model="sentence-transformers/all-MiniLM-L6-v2"))
context_recall = ContextRecall(llm=judge)
context_precision = ContextPrecisionWithoutReference(llm=judge)


# ---- The RAG pipeline under test ----
def retrieve(question: str) -> list[str]:
    return kb.query(query_texts=[question], n_results=3)["documents"][0]


def generate(question: str, contexts: list[str]) -> str:
    return client.responses.create(
        model="gpt-4o-mini",
        instructions="You are an insurance policy assistant. Answer using ONLY the policy context. Keep it short.",
        input="Policy context:\n" + "\n".join(f"- {c}" for c in contexts) + f"\n\nQuestion: {question}",
    ).output_text


# ---- Test cases: question + a reference answer written from the KB ----
TEST_CASES = [
    ("What documents are required to file a cashless health insurance claim at a network hospital, "
     "and within what time should hospitalization be intimated to the insurer?",
     "For a cashless claim at a network hospital, the policyholder submits a pre-authorization form "
     "to the Third Party Administrator (TPA). Hospitalization must be intimated within 24 hours for "
     "emergency admissions (24 to 48 hours for planned admissions). Claim documents typically include "
     "the claim form, original bills, discharge summary, prescription, and diagnostic test reports, "
     "and the TPA verifies the bills and coordinates settlement between the hospital and the insurer."),
    ("Is a pre-existing disease covered immediately under a new health insurance policy, and what "
     "happens to my coverage if I miss paying my premium on the due date?",
     "No - pre-existing diseases are usually covered only after a waiting period of 2 to 4 years from "
     "the policy start date. If a premium is not paid by the due date, insurers typically offer a grace "
     "period of 15 to 30 days during which the policy remains in force."),
]

totals = {"faithfulness": 0, "answer_relevancy": 0, "context_recall": 0, "context_precision": 0}

for question, reference in TEST_CASES:
    contexts = retrieve(question)
    response = generate(question, contexts)
    scores = {
        "faithfulness": faithfulness.score(user_input=question, response=response, retrieved_contexts=contexts).value,
        "answer_relevancy": answer_relevancy.score(user_input=question, response=response).value,
        "context_recall": context_recall.score(user_input=question, retrieved_contexts=contexts, reference=reference).value,
        "context_precision": context_precision.score(user_input=question, response=response, retrieved_contexts=contexts).value,
    }

    print("=" * 70 + f"\nQUESTION: {question}\n")
    print("CONTEXT:\n" + "\n".join(f"  - {c}" for c in contexts))
    print(f"\nRESPONSE: {response}\n")
    for metric, value in scores.items():
        print(f"  {metric:<18} {value:.2f}")
        totals[metric] += value

print("=" * 70 + "\nAVERAGES")
for metric, total in totals.items():
    print(f"  {metric:<18} {total / len(TEST_CASES):.2f}")
