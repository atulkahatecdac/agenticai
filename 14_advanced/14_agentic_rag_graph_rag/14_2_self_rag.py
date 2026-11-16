# Self-RAG: retrieve -> draft -> critique the draft -> regenerate if needed.
#
# Corrective RAG (14_3) grades the retrieved DOCUMENTS. Self-RAG grades the
# generated ANSWER: is every claim backed by the context, and is the whole
# question answered? This catches answers that overreach even when the
# retrieved chunks were relevant. Both questions below sit at the edge of
# what the insurance-policy knowledge base actually says.

import os
import sys
import json
import chromadb
from dotenv import load_dotenv
from pydantic import BaseModel
from langchain_openai import ChatOpenAI

load_dotenv(override=True)
sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(BASE_DIR, "policy_documents.json"), encoding="utf-8") as f:
    documents = json.load(f)

kb = chromadb.Client().create_collection("policy_docs")
kb.add(ids=[str(i) for i in range(len(documents))], documents=documents)

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
MAX_REGENERATIONS = 2


class Critique(BaseModel):
    is_supported: bool  # every claim backed by the context, nothing invented
    is_complete: bool   # every part of the question answered (as far as the context allows)
    feedback: str       # what to fix in the next draft


def retrieve(question: str) -> str:
    chunks = kb.query(query_texts=[question], n_results=3)["documents"][0]
    return "\n".join(f"- {c}" for c in chunks)


def draft(question: str, context: str, feedback: str = "") -> str:
    prompt = ("Answer using ONLY the context. Be concise. If the context doesn't say "
              "something, say so instead of guessing.\n")
    if feedback:
        prompt += f"Fix this from the previous draft: {feedback}\n"
    return llm.invoke(f"{prompt}\nContext:\n{context}\n\nQuestion: {question}").content


def critique(question: str, context: str, answer: str) -> Critique:
    return llm.with_structured_output(Critique).invoke(
        f"Question: {question}\n\nContext:\n{context}\n\nDraft answer:\n{answer}\n\n"
        "Is every claim in the draft backed by the context (no rounding up, no invented "
        "details), and does it fully answer the question?"
    )


def self_rag(question: str) -> str:
    context = retrieve(question)
    print(f"[retrieve]\n{context}")

    answer = draft(question, context)
    print(f"[draft] {answer}")

    for attempt in range(1, MAX_REGENERATIONS + 1):
        verdict = critique(question, context, answer)
        print(f"[critique #{attempt}] supported={verdict.is_supported} "
              f"complete={verdict.is_complete} - {verdict.feedback}")
        if verdict.is_supported and verdict.is_complete:
            break
        answer = draft(question, context, verdict.feedback)
        print(f"[regenerate #{attempt}] {answer}")

    return answer


QUESTIONS = [
    "I've had my health insurance for 3 years. Will my pre-existing diabetes be covered now, "
    "and can I switch to a different insurer without losing this benefit?",
    "My premium was due last month and I forgot to pay - is my policy still active, and if "
    "I let it lapse completely will a new claim still be honored?",
]

for question in QUESTIONS:
    print("\n" + "=" * 70 + f"\nQUESTION: {question}\n" + "=" * 70)
    print(f"\nFINAL ANSWER: {self_rag(question)}")
