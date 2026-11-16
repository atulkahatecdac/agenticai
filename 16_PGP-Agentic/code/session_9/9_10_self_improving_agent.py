# Self-improvement from failures: a judge grades each answer against the
# real policy. A low score (< 7) stores the CORRECTED FACT as a lesson; good
# answers leave no trace. Later, a different question recalls that lesson
# and gets it right. Nothing loops within one query (unlike 9_1) - the
# improvement shows up on the NEXT query.
# The judge's ground truth is real rows from customer_support_qa_500.csv.

import os
import sys
import pandas as pd
import chromadb
from dotenv import load_dotenv
from pydantic import BaseModel
from langchain_openai import ChatOpenAI

load_dotenv(override=True)
sys.stdout.reconfigure(encoding="utf-8")

THRESHOLD = 7
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
answers = pd.read_csv(os.path.join(BASE_DIR, "customer_support_qa_500.csv")).set_index("question")["answer"]

# What the judge knows (the agent never sees this). Two facts are probed below, two are distractors.
POLICY = "\n".join(f"- {answers[q]}" for q in [
    "How long does a refund take to appear on my statement?",
    "Why is my account locked after failed login attempts?",
    "Why can't I upload photos or files?",
    "How long does my login session last before timing out?",
])

lessons = chromadb.Client().create_collection("lessons")
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)


class Critique(BaseModel):
    score: int           # 1-10: 7+ only for the specific, correct fact
    corrected_fact: str  # short general lesson if the answer missed the fact, else ""


def recall_lessons(query: str) -> list[str]:
    if lessons.count() == 0:
        return []
    return lessons.query(query_texts=[query], n_results=min(2, lessons.count()))["documents"][0]


def respond(query: str, recalled: list[str]) -> str:
    return llm.invoke(
        "You are a customer support agent. Answer briefly and directly.\n\n"
        "Lessons from past mistakes (apply if relevant):\n" + ("\n".join(f"- {l}" for l in recalled) or "(none yet)")
        + f"\n\nCustomer question: {query}"
    ).content


def evaluate(query: str, answer: str) -> Critique:
    return llm.with_structured_output(Critique).invoke(
        "Grade this support answer against the ACTUAL policy. Be strict: 7+ only if it states the "
        "specific correct fact, not generic advice. If it missed, give the correct fact as a short "
        f"general lesson.\n\nPolicy:\n{POLICY}\n\nQuestion: {query}\nAnswer: {answer}"
    )


def maybe_store_lesson(critique: Critique):
    if critique.score < THRESHOLD and critique.corrected_fact:
        lessons.add(ids=[str(lessons.count())], documents=[critique.corrected_fact])
        print(f"[maybe_store_lesson] stored: {critique.corrected_fact}")
    else:
        print("[maybe_store_lesson] nothing stored")


def run(query: str):
    print(f"\nQUERY: {query}")
    recalled = recall_lessons(query)
    print(f"[recall_lessons] {recalled or 'none'}")
    answer = respond(query, recalled)
    print(f"[respond] {answer}")
    critique = evaluate(query, answer)
    print(f"[evaluate] score={critique.score}/10")
    maybe_store_lesson(critique)


print("=" * 70 + "\nPAIR 1: refund timing\n" + "=" * 70)
run("How long will it take for my refund to show up?")
run("I requested a refund 3 days ago and it's not showing yet - should I be worried?")

print("\n" + "=" * 70 + "\nPAIR 2: account lockout\n" + "=" * 70)
run("Why did my account suddenly get locked when I was trying to log in?")
run("How long do I need to wait before I can try logging into my account again?")
