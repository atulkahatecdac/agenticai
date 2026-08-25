import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")

import os
import shutil
import sys
from typing import TypedDict
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain_chroma import Chroma
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langgraph.graph import StateGraph, START, END

load_dotenv(override=True)
sys.stdout.reconfigure(encoding="utf-8")

# =====================================================================
# Self-improving agent: an evaluation score doesn't just grade one
# answer, it decides whether to persist a lesson that changes FUTURE
# answers on different, unrelated queries. Unlike multi_turn_reflection.py
# (which loops within a single task until it scores well), nothing here
# loops - each query runs the graph once, and improvement shows up
# later, on a completely different query that benefits from a lesson an
# earlier query's low score left behind in a real persistent store.
# =====================================================================

THRESHOLD = 7

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PERSIST_DIR = os.path.join(BASE_DIR, "self_improving_lessons_db")
shutil.rmtree(PERSIST_DIR, ignore_errors=True)

vectorstore = Chroma(
    collection_name="lessons",
    embedding_function=OpenAIEmbeddings(model="text-embedding-3-small"),
    persist_directory=PERSIST_DIR,
)

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
judge_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)


class SelfImprovingState(TypedDict):
    query: str
    retrieved_lessons: list[str]
    response: str
    score: int
    corrected_fact: str


def recall_lessons(state: SelfImprovingState) -> SelfImprovingState:
    if vectorstore.get()["ids"]:
        matches = vectorstore.similarity_search(state["query"], k=2)
        lessons = [m.page_content for m in matches]
    else:
        lessons = []
    print(f"[recall_lessons] {len(lessons)} relevant lesson(s) found")
    return {"retrieved_lessons": lessons}


def respond(state: SelfImprovingState) -> SelfImprovingState:
    context = "\n".join(f"- {lesson}" for lesson in state["retrieved_lessons"])
    prompt = f"""You are a bank customer support agent. Answer the customer's question briefly and directly.

Lessons learned from past mistakes - apply these if relevant:
{context or "(none yet)"}

Customer question: {state['query']}"""
    response = llm.invoke(prompt)
    print(f"[respond] {response.content}")
    return {"response": response.content}


class Critique(BaseModel):
    score: int = Field(description="1-10: does the answer state a concrete, correct, checkable fact "
                        "(exact figure, phone number, policy detail) rather than generic hedging advice?")
    corrected_fact: str = Field(description="If the answer missed or hedged on a concrete fact, state the "
                                 "correct fact as a short, standalone, general lesson for future answers "
                                 "(e.g. 'The daily ATM withdrawal limit is $500.'). Empty string if the "
                                 "answer was already accurate and specific.")


REAL_BANK_POLICY = """- Daily ATM withdrawal limit: $500
- Lost/stolen card hotline: 1-800-555-0199, available 24/7
- Duplicate-looking charges are usually a pending authorization hold that clears in 3-5 business days
- Gambling and cryptocurrency purchases are blocked by default under Merchant Controls"""


def evaluate(state: SelfImprovingState) -> SelfImprovingState:
    prompt = f"""Grade this bank support answer against the ACTUAL policy reference below. Be strict -
score 7+ only if the answer states the specific correct fact, not just plausible-sounding generic advice.

Actual policy reference (the grader's source of truth, not shown to the agent):
{REAL_BANK_POLICY}

Customer question: {state['query']}
Answer to grade: {state['response']}"""
    verdict = judge_llm.with_structured_output(Critique).invoke(prompt)
    print(f"[evaluate] score={verdict.score}/10" + (f" - lesson: {verdict.corrected_fact}" if verdict.corrected_fact else ""))
    return {"score": verdict.score, "corrected_fact": verdict.corrected_fact}


def maybe_store_lesson(state: SelfImprovingState) -> SelfImprovingState:
    if state["score"] < THRESHOLD and state["corrected_fact"]:
        vectorstore.add_texts([state["corrected_fact"]])
        print(f"[maybe_store_lesson] stored: {state['corrected_fact']}")
    else:
        print("[maybe_store_lesson] no lesson stored")
    return {}


graph = StateGraph(SelfImprovingState)
graph.add_node("recall_lessons", recall_lessons)
graph.add_node("respond", respond)
graph.add_node("evaluate", evaluate)
graph.add_node("maybe_store_lesson", maybe_store_lesson)
graph.add_edge(START, "recall_lessons")
graph.add_edge("recall_lessons", "respond")
graph.add_edge("respond", "evaluate")
graph.add_edge("evaluate", "maybe_store_lesson")
graph.add_edge("maybe_store_lesson", END)

app = graph.compile()


def run(query: str) -> None:
    print(f"\nQUERY: {query}")
    app.invoke({"query": query, "retrieved_lessons": [], "response": "", "score": 0, "corrected_fact": ""})


if __name__ == "__main__":
    print("=" * 70)
    print("PAIR 1: ATM withdrawal limit")
    print("=" * 70)
    run("What's the daily limit if I want to withdraw cash from an ATM?")
    run("I want to take out $800 in cash before my trip - can I just do that at one ATM?")

    print("\n" + "=" * 70)
    print("PAIR 2: lost/stolen card hotline")
    print("=" * 70)
    run("My wallet with my debit card just got stolen, what do I do?")
    run("I'm traveling and can't find my card, is there a number I can call anytime, even at night?")
