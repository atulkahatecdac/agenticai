import warnings
warnings.filterwarnings("ignore")

import json
import os
import shutil
import sys
import time
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_openai import ChatOpenAI

load_dotenv(override=True)
sys.stdout.reconfigure(encoding="utf-8")

# =====================================================================
# Is agentic RAG worth it? Measure, don't guess.
#
# Two pipelines answer the SAME test set over the SAME knowledge base,
# and the SAME judge scores both:
#
#   standard : retrieve top-3 -> answer                    (1 LLM call)
#   agentic  : rewrite the query -> retrieve -> grade the chunks ->
#              if not enough, retry with a new query -> answer, or say
#              "not in the knowledge base"                 (3-5 LLM calls)
#
# The test set mixes easy questions, questions worded differently from
# the KB, two-part questions, and questions the KB cannot answer -
# where the right reply is to decline, not to guess.
# =====================================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PERSIST_DIR = os.path.join(BASE_DIR, "benchmark_chroma_db")
shutil.rmtree(PERSIST_DIR, ignore_errors=True)
with open(os.path.join(BASE_DIR, "policy_documents.json"), encoding="utf-8") as f:
    KB = json.load(f)

store = Chroma(collection_name="policy_docs", persist_directory=PERSIST_DIR,
               embedding_function=HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2"))
store.add_texts(KB)
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
NOT_FOUND = "NOT IN KNOWLEDGE BASE"

TEST_SET = [
    # (question, reference answer, kind)
    ("What is the free-look period for a new health policy?", "15 to 30 days, to cancel and get a refund", "easy"),
    ("How long is the waiting period for maternity benefits?", "usually 9 months (some plans longer)", "easy"),
    ("I crashed my car - how soon do I have to tell the insurance company?", "within 24 to 48 hours of the accident", "reworded"),
    ("Is my eye-lens operation covered if I go home the same day?", "yes - day-care procedures such as cataract surgery are covered without 24-hour hospitalisation", "reworded"),
    ("What does a burglary claim need, and what is excluded from home insurance?", "a police FIR and a list of stolen items; wear and tear / poor maintenance is excluded", "two-part"),
    ("For a lost bag abroad, what report do I need, and are pre-existing illnesses covered?", "a property irregularity report from the airline; pre-existing conditions are generally excluded unless covered", "two-part"),
    ("My claim was turned down because of my paragliding hobby. Was that allowed, and who can I complain to if the insurer won't budge?",
     "yes - adventure sports are usually excluded unless a rider was bought; an ombudsman can be approached if the insurer's grievance process fails", "hard"),
    ("My father's diabetes started before he bought his health policy. When will it be covered, can he change insurers without starting that wait again, and what if he forgets a premium?",
     "pre-existing diseases are covered after a 2-4 year waiting period; portability keeps continuity benefits such as waiting periods served; a grace period of 15-30 days applies to a missed premium", "hard"),
    ("What is the premium for a 35-year-old non-smoker's term plan?", NOT_FOUND, "not in KB"),
    ("Does pet insurance cover vet visits?", NOT_FOUND, "not in KB"),
]

ANSWER_RULES = f"Answer from the context only, in one or two sentences. If the context does not contain the answer, reply exactly: {NOT_FOUND}"


def context_for(query: str, k: int = 3) -> list[str]:
    return [d.page_content for d in store.similarity_search(query, k=k)]


# ---------------------------------------------------------------------
# Pipeline 1: standard RAG
# ---------------------------------------------------------------------
def standard_rag(question: str) -> tuple[str, int]:
    ctx = "\n".join(context_for(question))
    return llm.invoke(f"{ANSWER_RULES}\n\nContext:\n{ctx}\n\nQuestion: {question}").content, 1


# ---------------------------------------------------------------------
# Pipeline 2: agentic RAG (query rewriting + grading + one retry)
# ---------------------------------------------------------------------
class Queries(BaseModel):
    queries: list[str] = Field(description="1-2 short search queries in insurance-policy wording; one per part of a two-part question")


class Grade(BaseModel):
    enough: bool = Field(description="Does the context fully answer every part of the question?")
    missing: str = Field(description="What is still missing, or '' if nothing")


def agentic_rag(question: str) -> tuple[str, int]:
    calls = 0
    queries = llm.with_structured_output(Queries).invoke(
        f"Rewrite this customer question as search queries for an insurance policy knowledge base:\n{question}"
    ).queries
    calls += 1
    chunks: list[str] = []
    for attempt in range(2):
        for q in queries:
            chunks += [c for c in context_for(q) if c not in chunks]
        grade = llm.with_structured_output(Grade).invoke(
            f"Question: {question}\n\nContext:\n" + "\n".join(chunks)
        )
        calls += 1
        if grade.enough or attempt == 1:
            break
        queries = [grade.missing or question]                  # retry: search for what is missing
    answer = llm.invoke(f"{ANSWER_RULES}\n\nContext:\n" + "\n".join(chunks) + f"\n\nQuestion: {question}").content
    return answer, calls + 1


# ---------------------------------------------------------------------
# One judge for both - LLM-as-a-judge (Module 09) against the reference.
# ---------------------------------------------------------------------
class Verdict(BaseModel):
    correct: bool = Field(description="Does the answer agree with the reference on every point?")


def judge(question: str, reference: str, answer: str) -> bool:
    if reference == NOT_FOUND:                                  # declining is the only right answer
        return NOT_FOUND.lower() in answer.lower()
    return llm.with_structured_output(Verdict).invoke(
        f"Question: {question}\nReference answer: {reference}\nCandidate answer: {answer}\n"
        "Is the candidate correct and complete compared with the reference? Extra harmless detail is fine."
    ).correct


if __name__ == "__main__":
    results = {"standard": [], "agentic": []}
    for question, reference, kind in TEST_SET:
        print(f"\n[{kind}] {question}")
        for name, pipeline in (("standard", standard_rag), ("agentic", agentic_rag)):
            start = time.perf_counter()
            answer, calls = pipeline(question)
            seconds = time.perf_counter() - start
            ok = judge(question, reference, answer)
            results[name].append({"kind": kind, "ok": ok, "s": seconds, "calls": calls})
            print(f"   {name:8} {'PASS' if ok else 'FAIL'}  {seconds:4.1f}s  {calls} call(s)  {answer[:110]}")

    print("\n" + "=" * 72)
    kinds = ["easy", "reworded", "two-part", "hard", "not in KB"]
    print(f"{'':10}{'accuracy':>9}" + "".join(f"{k:>10}" for k in kinds) + f"{'avg s':>7}{'calls':>7}")
    summary = {}
    for name, rows in results.items():
        by = lambda k: f"{sum(r['ok'] for r in rows if r['kind'] == k)}/{sum(r['kind'] == k for r in rows)}"
        summary[name] = (sum(r["ok"] for r in rows), sum(r["calls"] for r in rows), sum(r["s"] for r in rows) / len(rows))
        print(f"{name:10}{summary[name][0] / len(rows):>9.0%}" + "".join(f"{by(k):>10}" for k in kinds)
              + f"{summary[name][2]:>7.1f}{summary[name][1]:>7}")
    print("=" * 72)
    (s_ok, s_calls, s_sec), (a_ok, a_calls, a_sec) = summary["standard"], summary["agentic"]
    print(f"Agentic RAG: {a_ok - s_ok:+d} correct answers for {a_calls / s_calls:.1f}x the LLM calls "
          f"and {a_sec / s_sec:.1f}x the latency.")
    print("Decide per use case: if the extra answers are on the questions your users actually ask,")
    print("pay for it (or route only hard questions to it); if not, keep standard RAG.")
