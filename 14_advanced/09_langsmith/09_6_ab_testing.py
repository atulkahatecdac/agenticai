import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)
# Harmless pydantic warning from with_structured_output() calls elsewhere
# in this directory's sibling files - filtered here too for consistency.
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")

import csv
import os
import sys
import time
from dotenv import load_dotenv

load_dotenv(override=True)

# .env's LANGSMITH_PROJECT is shared with another exercise (a CrewAI
# demo) - use a dedicated project so this script's experiments don't mix in.
os.environ["LANGSMITH_PROJECT"] = "agenticai-09-langsmith-demo"

# LLM output can contain characters outside Windows' default console
# codepage (cp1252) - reconfigure stdout to UTF-8 so printing doesn't crash.
sys.stdout.reconfigure(encoding="utf-8")

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_openai import ChatOpenAI
from langsmith import Client, evaluate
from langsmith.evaluation import evaluate_comparative
from langsmith.schemas import Example

# =====================================================================
# A/B testing with LangSmith - pairwise preference comparison, not
# reference grading.
#
# 09_5_prompt_regression_testing.py (same directory) asks "does this answer
# match the known-correct reference?" - useful when there IS one right
# answer. A/B testing is for the opposite case: two variants that are
# both factually fine, where the real question is which one a customer
# would PREFER. Both variants here are grounded in the SAME retrieved
# FAQ answer, so factual correctness is held constant - the only
# variable being tested is response STYLE (concise vs warm/detailed).
#
# Mechanically: run each variant as its own evaluate() experiment (no
# per-example scoring needed - nothing to grade against a reference),
# then evaluate_comparative() pulls both experiments' runs for the same
# example and hands them BOTH to one judge call that picks a winner.
# =====================================================================

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
judge_llm = ChatOpenAI(model="gpt-4o", temperature=0)  # separate, stronger judge model

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, "..", "..", "3_langgraph", "Dataset_Banking_chatbot.csv")

with open(CSV_PATH, newline="", encoding="utf-8") as f:
    faq_rows = list(csv.DictReader(f))[:6]  # same 6 rows as 09_5_prompt_regression_testing.py

vectorstore = Chroma.from_documents(
    [Document(page_content=row["Query"], metadata={"answer": row["Response"]}) for row in faq_rows],
    embedding=HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2"),
)

DATASET_NAME = "agenticai-09-langsmith-banking-regression-demo"  # same dataset, reused
examples = [{"inputs": {"question": row["Query"]}, "outputs": {"answer": row["Response"]}} for row in faq_rows]

client = Client()
if client.has_dataset(dataset_name=DATASET_NAME):
    client.delete_dataset(dataset_name=DATASET_NAME)
client.create_dataset(DATASET_NAME)
client.create_examples(dataset_name=DATASET_NAME, examples=examples)


def _grounded_answer(question: str, style_instruction: str) -> str:
    match = vectorstore.similarity_search(question, k=1)[0]
    prompt = f"""Answer this bank customer's question using the reference FAQ answer below as the \
source of truth. {style_instruction}

Reference FAQ answer: {match.metadata['answer']}
Customer question: {question}"""
    return llm.invoke(prompt).content


def predict_a(inputs: dict) -> dict:
    # VARIANT A: concise, just the facts.
    return {"answer": _grounded_answer(inputs["question"], "Keep it to one short, direct sentence.")}


def predict_b(inputs: dict) -> dict:
    # VARIANT B: warm and a bit more detailed.
    return {"answer": _grounded_answer(inputs["question"], "Be warm and friendly, briefly explaining why, in 2-3 sentences.")}


def score_preference(runs: list, example: Example) -> dict:
    pred_a, pred_b = runs[0].outputs["answer"], runs[1].outputs["answer"]
    prompt = f"""A bank customer asked: {example.inputs['question']}

Option A: {pred_a}

Option B: {pred_b}

Both are factually accurate. Which would a customer prefer, considering clarity, tone, and \
helpfulness? Reply with exactly one word: A or B."""
    winner = "A" if judge_llm.invoke(prompt).content.strip().upper().startswith("A") else "B"
    scores = {runs[0].id: 1, runs[1].id: 0} if winner == "A" else {runs[0].id: 0, runs[1].id: 1}
    return {"key": "preference", "scores": scores, "comment": f"Preferred option {winner}"}


if __name__ == "__main__":
    print("Running variant A (concise)...")
    results_a = evaluate(predict_a, data=DATASET_NAME, experiment_prefix="ab-variant-a-concise")

    print("Running variant B (warm/detailed)...")
    results_b = evaluate(predict_b, data=DATASET_NAME, experiment_prefix="ab-variant-b-detailed")

    # evaluate() blocks until local execution finishes, but LangSmith
    # indexes uploaded runs server-side asynchronously - evaluate_comparative()
    # queries for both experiments' runs immediately, and any run that
    # hasn't landed yet is silently dropped rather than retried. A short
    # wait here is simpler than a per-run retry loop for 12 runs.
    time.sleep(5)

    print("\nRunning pairwise comparison...")
    comparison = evaluate_comparative(
        (results_a.experiment_name, results_b.experiment_name),
        evaluators=[score_preference],
    )

    a_wins = b_wins = 0
    for row in comparison:
        question = row["example"].inputs["question"]
        run_a, run_b = row["evaluation_results"]["runs"]
        feedback = row["evaluation_results"]["feedback.preference"]
        winner = "A" if feedback.scores[run_a.id] == 1 else "B"
        a_wins += winner == "A"
        b_wins += winner == "B"

        print(f"\nQ: {question}")
        print(f"  A (concise):  {run_a.outputs['answer']}")
        print(f"  B (detailed): {run_b.outputs['answer']}")
        print(f"  Winner: {winner} - {feedback.comment}")

    print(f"\nA (concise) wins:  {a_wins}/{len(examples)}")
    print(f"B (detailed) wins: {b_wins}/{len(examples)}")
