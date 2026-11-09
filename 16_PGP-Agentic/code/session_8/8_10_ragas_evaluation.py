import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")

import json
import os
import shutil
import sys
from dotenv import load_dotenv
from openai import AsyncOpenAI, OpenAI
from ragas.embeddings import HuggingFaceEmbeddings as RagasHuggingFaceEmbeddings
from ragas.llms import llm_factory
from ragas.metrics.collections import AnswerRelevancy, ContextPrecisionWithoutReference, ContextRecall, Faithfulness
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

load_dotenv(override=True)
sys.stdout.reconfigure(encoding="utf-8")

# =====================================================================
# RAGAS Evaluation: none of the other scripts in this folder actually
# SCORE their own output - they print a before/after and leave it to the
# reader's eyes. RAGAS instead runs an LLM judge over a retrieve() /
# generate() pipeline and produces numeric metrics, so pipeline changes
# (a different retriever, a different prompt, a different top_n) can be
# compared objectively instead of by vibes.
#
# Four core metrics, each answering a different question:
#   Faithfulness       - does the answer only claim things that are
#                         actually IN the retrieved context, or did the
#                         model add/invent something?
#   Answer Relevancy   - does the answer actually address what was
#                         asked (vs. a vague non-answer)?
#   Context Recall     - did retrieval find what the REFERENCE answer
#                         needed? (ground truth = a hand-written
#                         reference answer grounded in the KB)
#   Context Precision  - of what was retrieved, how much was actually
#                         useful for the answer given?
#
# Knowledge base: the same 50-statement insurance policy KB used
# elsewhere in this folder. The two test cases below reuse the same two
# core questions used throughout this folder, each paired with a
# reference answer written directly from the KB statements that answer
# it - so RAGAS is scoring the same pipeline the other scripts explore.
# =====================================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PERSIST_DIR = os.path.join(BASE_DIR, "ragas_chroma_db")
shutil.rmtree(PERSIST_DIR, ignore_errors=True)

with open(os.path.join(BASE_DIR, "policy_documents.json"), encoding="utf-8") as f:
    POLICY_DOCUMENTS = json.load(f)

vectorstore = Chroma(
    collection_name="policy_docs",
    embedding_function=HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2"),
    persist_directory=PERSIST_DIR,
)
vectorstore.add_texts(POLICY_DOCUMENTS)

MODEL = "gpt-4o-mini"
TOP_K = 3

openai_client = OpenAI()

# ragas's score() calls the LLM's async methods internally, even for "sync" usage - it
# needs an AsyncOpenAI client.
ragas_llm = llm_factory(model=MODEL, provider="openai", client=AsyncOpenAI())
ragas_embeddings = RagasHuggingFaceEmbeddings(model="sentence-transformers/all-MiniLM-L6-v2")

faithfulness = Faithfulness(llm=ragas_llm)
answer_relevancy = AnswerRelevancy(llm=ragas_llm, embeddings=ragas_embeddings)
context_recall = ContextRecall(llm=ragas_llm)
context_precision = ContextPrecisionWithoutReference(llm=ragas_llm)


def retrieve(question: str) -> list[str]:
    return [doc.page_content for doc in vectorstore.similarity_search(question, k=TOP_K)]


def generate(question: str, contexts: list[str]) -> str:
    context = "\n".join(f"- {c}" for c in contexts)
    response = openai_client.responses.create(
        model=MODEL,
        instructions=(
            "You are an insurance policy assistant. Answer using ONLY the policy context "
            "below - do not invent coverage terms. Keep it short."
        ),
        input=f"Policy context:\n{context}\n\nCustomer question: {question}",
    )
    return response.output_text


TEST_CASES = [
    {
        "question": "What documents are required to file a cashless health insurance claim at "
        "a network hospital, and within what time should hospitalization be intimated to the "
        "insurer?",
        "reference": "For a cashless claim at a network hospital, the policyholder submits a "
        "pre-authorization form to the Third Party Administrator (TPA). Hospitalization must "
        "be intimated within 24 hours for emergency admissions (24 to 48 hours for planned "
        "admissions). Claim documents typically include the claim form, original bills, "
        "discharge summary, prescription, and diagnostic test reports, and the TPA verifies "
        "the bills and coordinates settlement between the hospital and the insurer.",
    },
    {
        "question": "Is a pre-existing disease covered immediately under a new health insurance "
        "policy, and what happens to my coverage if I miss paying my premium on the due date?",
        "reference": "No - pre-existing diseases are usually covered only after a waiting "
        "period of 2 to 4 years from the policy start date. If a premium is not paid by the "
        "due date, insurers typically offer a grace period of 15 to 30 days during which the "
        "policy remains in force.",
    },
]


def evaluate_case(question: str, reference: str) -> dict:
    contexts = retrieve(question)
    response = generate(question, contexts)

    return {
        "question": question,
        "response": response,
        "retrieved_contexts": contexts,
        "faithfulness": faithfulness.score(
            user_input=question, response=response, retrieved_contexts=contexts
        ).value,
        "answer_relevancy": answer_relevancy.score(user_input=question, response=response).value,
        "context_recall": context_recall.score(
            user_input=question, retrieved_contexts=contexts, reference=reference
        ).value,
        "context_precision": context_precision.score(
            user_input=question, response=response, retrieved_contexts=contexts
        ).value,
    }


if __name__ == "__main__":
    results = []

    for case in TEST_CASES:
        print("=" * 70)
        print(f"QUESTION: {case['question']}")

        result = evaluate_case(case["question"], case["reference"])
        results.append(result)

        print(f"\nRETRIEVED CONTEXT ({len(result['retrieved_contexts'])} chunk(s)):")
        for c in result["retrieved_contexts"]:
            print(f"  - {c}")

        print(f"\nRESPONSE: {result['response']}")
        print(f"Faithfulness:       {result['faithfulness']:.2f}")
        print(f"Answer Relevancy:   {result['answer_relevancy']:.2f}")
        print(f"Context Recall:     {result['context_recall']:.2f}")
        print(f"Context Precision:  {result['context_precision']:.2f}")
        print()

    print("=" * 70)
    print("AVERAGES ACROSS ALL TEST CASES")
    for metric in ["faithfulness", "answer_relevancy", "context_recall", "context_precision"]:
        avg = sum(r[metric] for r in results) / len(results)
        print(f"  {metric}: {avg:.2f}")
