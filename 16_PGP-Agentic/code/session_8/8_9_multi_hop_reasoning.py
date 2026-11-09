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
# Multi-Hop Reasoning: answering a question by following a CHAIN of
# relationships across several documents, rather than finding the whole
# answer sitting in one chunk. A single similarity search over the
# question tends to retrieve chunks that all resemble the question's
# wording - it has no mechanism for realizing "now that I know X, I
# also need Y to finish the chain." Multi-hop retrieval fixes this by
# looping: retrieve, read what came back, decide what fact is STILL
# missing to close the chain, retrieve again for that specific gap, and
# repeat until nothing is missing - then apply any numeric/timing
# condition in the question to the accumulated facts to reach a verdict.
#
# Knowledge base: the same 50-statement insurance policy KB used
# elsewhere in this folder. The two questions below each require
# chaining 3-4 separate chunks (a benefit's rule, a timing condition,
# who processes it, how long it takes) that a single top-k search
# rarely surfaces together, since each chunk is worded around a
# different part of the story.
# =====================================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PERSIST_DIR = os.path.join(BASE_DIR, "multihop_chroma_db")
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

MAX_HOPS = 4


class HopDecision(BaseModel):
    done: bool = Field(description="True only if the facts gathered so far are enough to fully "
                        "answer every part of the question, including checking any specific "
                        "number, date, or timing mentioned in the question against a rule found "
                        "in the facts.")
    reasoning: str = Field(description="One sentence: what part of the question is still unanswered "
                            "given the facts gathered so far.")
    next_hop_query: str = Field(description="If not done, a short, specific search query for the "
                                 "ONE missing fact needed to continue the chain (e.g. who processes "
                                 "it, or how long that step takes). Empty string if done.")


class FinalAnswer(BaseModel):
    condition_check: str = Field(description="Explicitly state any specific number/date/timing from "
                                  "the question and whether it satisfies the relevant rule found in "
                                  "the gathered facts.")
    answer: str = Field(description="The final answer to the question, concise.")


def multi_hop_retrieve(question: str) -> list[str]:
    gathered: list[str] = []
    seen = set()
    current_query = question

    for hop in range(1, MAX_HOPS + 1):
        docs = vectorstore.similarity_search(current_query, k=2)
        new_docs = [d.page_content for d in docs if d.page_content not in seen]
        if not new_docs:
            print(f"  [hop {hop}] no new facts found - stopping")
            break
        for text in new_docs:
            seen.add(text)
            gathered.append(text)
        print(f"  [hop {hop}] query: {current_query!r}")
        for text in new_docs:
            print(f"           + {text}")

        decision = llm.with_structured_output(HopDecision).invoke(
            f"Original question: {question}\n\n"
            "Facts gathered so far:\n" + "\n".join(f"- {g}" for g in gathered) + "\n\n"
            "Decide whether these facts are enough to fully answer the question end-to-end, "
            "including checking any specific number/date/timing in the question against a rule "
            "in the facts. If not, give a short search query for the ONE next fact needed."
        )
        print(f"           reasoning: {decision.reasoning}")
        if decision.done:
            break
        current_query = decision.next_hop_query

    return gathered


def answer_from(label: str, question: str, context: list[str]) -> None:
    context_block = "\n".join(f"- {c}" for c in context) or "(no supporting context found)"
    result = llm.with_structured_output(FinalAnswer).invoke(
        f"Answer the question using ONLY the context below. If the question includes a specific "
        f"number/date/timing, explicitly check it against any relevant rule in the context first.\n\n"
        f"Context:\n{context_block}\n\nQuestion: {question}"
    )
    print(f"\n{label}")
    print(f"  condition check: {result.condition_check}")
    print(f"  answer:          {result.answer}")


QUESTIONS = [
    "I'm on a Family Floater Gold health insurance plan and had an emergency hospitalization at "
    "a network hospital. I got the hospitalization intimated to the insurer 20 hours after "
    "admission and want a cashless claim - will it be accepted, who processes it, and how long "
    "will settlement take once all documents are in?",

    "My mother is a senior citizen on a health insurance policy with a co-payment clause. She "
    "was treated for a planned surgery at a hospital that is NOT in the insurer's network, and "
    "she intimated the insurer 40 hours in advance. Will her claim be cashless or reimbursement, "
    "will she have to pay a share herself, and within how many days after discharge must she "
    "submit her bills?",
]

for question in QUESTIONS:
    print("\n" + "=" * 70)
    print(f"QUESTION: {question}")
    print("=" * 70)

    # -----------------------------
    # BEFORE: a single similarity search over the whole question. It
    # retrieves chunks that resemble the question's wording, but has no
    # way to notice a piece of the chain is still missing.
    # -----------------------------
    single_hop_docs = [d.page_content for d in vectorstore.similarity_search(question, k=3)]
    print("\nBEFORE (single-hop retrieval, top 3):")
    for doc in single_hop_docs:
        print(f"  - {doc}")
    answer_from("BEFORE ANSWER (single-hop context):", question, single_hop_docs)

    # -----------------------------
    # AFTER: loop - retrieve, decide what's still missing, retrieve
    # again for that specific gap - until the chain is complete.
    # -----------------------------
    print("\nAFTER (multi-hop retrieval):")
    multi_hop_docs = multi_hop_retrieve(question)
    answer_from(
        f"AFTER ANSWER (multi-hop context, {len(multi_hop_docs)} chunk(s) chained):",
        question,
        multi_hop_docs,
    )
