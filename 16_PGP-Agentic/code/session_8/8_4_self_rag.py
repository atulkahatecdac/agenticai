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
from pydantic import BaseModel, Field
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_openai import ChatOpenAI

load_dotenv(override=True)
sys.stdout.reconfigure(encoding="utf-8")

# =====================================================================
# Self-RAG: Retrieve -> Evaluate -> Regenerate -> Synthesize.
#
# Corrective RAG (see 8_5_corrective_rag.py) grades the RETRIEVED
# DOCUMENTS and decides where to get context from (KB vs. web search).
# Self-RAG grades the GENERATED ANSWER instead: after drafting a reply,
# it asks "is every claim in this draft actually backed by the context I
# retrieved, and does it fully answer what was asked?" If the draft
# overclaims something the KB doesn't actually support, or leaves part
# of the question unanswered, it regenerates - either with a stricter
# grounding instruction or a follow-up retrieval - before finalizing.
# This catches a failure mode CRAG can't: the retrieved documents were
# perfectly relevant, but the answer still overreached beyond them.
#
# Knowledge base: the same 50-statement insurance policy KB used
# elsewhere in this folder. Both questions below sit right at the edge
# of what the KB actually commits to - a natural first-draft answer is
# likely to round up ("3 years in" -> "yes, covered") or fill a real gap
# in the KB with a plausible-sounding invention, which is exactly what
# the critique step exists to catch.
# =====================================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PERSIST_DIR = os.path.join(BASE_DIR, "selfrag_chroma_db")
shutil.rmtree(PERSIST_DIR, ignore_errors=True)

with open(os.path.join(BASE_DIR, "policy_documents.json"), encoding="utf-8") as f:
    POLICY_DOCUMENTS = json.load(f)

vectorstore = Chroma(
    collection_name="policy_docs",
    embedding_function=HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2"),
    persist_directory=PERSIST_DIR,
)
vectorstore.add_texts(POLICY_DOCUMENTS)

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

MAX_REGENERATIONS = 2


class Critique(BaseModel):
    is_supported: bool = Field(description="True only if EVERY claim in the draft answer is "
                                "directly backed by the retrieved context - no rounding up, no "
                                "filling gaps with plausible-sounding assumptions.")
    is_useful: bool = Field(description="True if the draft fully addresses every part of the "
                             "question that the context is capable of answering.")
    critique: str = Field(description="One or two sentences on what's unsupported or "
                           "incomplete, and what the regenerated answer should do differently "
                           "(e.g. hedge a specific claim, or explicitly say the KB doesn't "
                           "specify something rather than guessing).")


def retrieve(question: str, k: int = 3) -> list[str]:
    return [doc.page_content for doc in vectorstore.similarity_search(question, k=k)]


def draft(question: str, context: list[str], guidance: str = "") -> str:
    context_block = "\n".join(f"- {c}" for c in context) or "(no supporting context found)"
    instruction = (
        "Answer the question using ONLY the context below. Be concise. If the context does not "
        "fully specify something, say so explicitly rather than guessing."
    )
    if guidance:
        instruction += f"\n\nAdditional guidance from a previous critique: {guidance}"
    return llm.invoke(f"{instruction}\n\nContext:\n{context_block}\n\nQuestion: {question}").content


def critique(question: str, context: list[str], answer: str) -> Critique:
    context_block = "\n".join(f"- {c}" for c in context)
    return llm.with_structured_output(Critique).invoke(
        f"Question: {question}\n\nContext used:\n{context_block}\n\nDraft answer:\n{answer}\n\n"
        "Critique the draft: is every claim in it actually backed by the context (no rounding "
        "up, no invented specifics), and does it fully address the question?"
    )


def self_rag(question: str) -> str:
    context = retrieve(question)
    print(f"  [retrieve] {len(context)} chunk(s)")
    for c in context:
        print(f"    - {c}")

    answer = draft(question, context)
    print(f"  [draft] {answer}")

    guidance = ""
    for attempt in range(1, MAX_REGENERATIONS + 1):
        verdict = critique(question, context, answer)
        print(f"  [evaluate #{attempt}] supported={verdict.is_supported} useful={verdict.is_useful} - {verdict.critique}")

        if verdict.is_supported and verdict.is_useful:
            break

        guidance = verdict.critique
        answer = draft(question, context, guidance=guidance)
        print(f"  [regenerate #{attempt}] {answer}")

    print("  [synthesize] final answer below")
    return answer


QUESTIONS = [
    "I've had my health insurance for 3 years. Will my pre-existing diabetes be covered now, "
    "and can I switch to a different insurer without losing this benefit?",

    "My health insurance premium was due last month and I forgot to pay - is my policy still "
    "active, and if I let it lapse completely will a new claim still be honored under it?",
]

for question in QUESTIONS:
    print("\n" + "=" * 70)
    print(f"QUESTION: {question}")
    print("=" * 70)
    final_answer = self_rag(question)
    print(f"\nFINAL ANSWER: {final_answer}")
