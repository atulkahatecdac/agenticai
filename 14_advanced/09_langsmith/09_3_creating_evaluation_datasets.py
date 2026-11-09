import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)
# Harmless pydantic warning triggered by with_structured_output() on every
# judge call below - pure noise, drowns out the actual demo output.
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")

import os
import sys
from dotenv import load_dotenv

load_dotenv(override=True)
os.environ["LANGSMITH_PROJECT"] = "agenticai-09-langsmith-demo"
sys.stdout.reconfigure(encoding="utf-8")

from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langsmith import Client, evaluate
from langsmith.schemas import Example, Run

# =====================================================================
# Building an evaluation dataset: each example pairs an input with an
# expected answer. A GOLDEN QA pair is a clear, trusted example with one
# correct answer. An EDGE CASE deliberately stresses the system
# (a misspelled question, missing information, a very long question) -
# both kinds belong in the same dataset, tagged via metadata so results
# can be compared category by category instead of as one blended score.
# =====================================================================

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

EXAMPLES = [
    {"inputs": {"question": "What is the daily ATM withdrawal limit on my debit card?"},
     "outputs": {"answer": "The daily ATM withdrawal limit is $500."},
     "metadata": {"category": "golden"}},
    {"inputs": {"question": "How do I report a lost or stolen credit card?"},
     "outputs": {"answer": "Call our 24/7 hotline at 1-800-555-0199 to report it immediately and freeze the card."},
     "metadata": {"category": "golden"}},
    {"inputs": {"question": "Wat is the daily ATM withdrawl limt on my debit crad?"},
     "outputs": {"answer": "The daily ATM withdrawal limit is $500."},
     "metadata": {"category": "edge_case", "edge_type": "misspelled_words"}},
    {"inputs": {"question": "Can you reverse it? It's not right."},
     "outputs": {"answer": "unanswerable - the question doesn't say which transaction or charge to reverse"},
     "metadata": {"category": "edge_case", "edge_type": "missing_information"}},
    {"inputs": {"question": "Hi, I've been a customer for about 6 years now and normally I don't have "
                             "any issues, but I was traveling last week and needed extra cash for the "
                             "trip and ended up going to a few different ATMs over a couple of days, and "
                             "now I'm trying to figure out - what's the actual daily limit on how much I "
                             "can pull out from an ATM using my debit card?"},
     "outputs": {"answer": "The daily ATM withdrawal limit is $500."},
     "metadata": {"category": "edge_case", "edge_type": "very_long_input"}},
]

DATASET_NAME = "agenticai-09-langsmith-eval-dataset-demo"

client = Client()
if client.has_dataset(dataset_name=DATASET_NAME):
    client.delete_dataset(dataset_name=DATASET_NAME)
client.create_dataset(DATASET_NAME)
client.create_examples(dataset_name=DATASET_NAME, examples=EXAMPLES)


def predict(inputs: dict) -> dict:
    prompt = f"Answer briefly. If the question is too ambiguous or missing information to answer, say so plainly.\n\nQuestion: {inputs['question']}"
    response = llm.invoke(prompt)
    return {"answer": response.content}


class Verdict(BaseModel):
    correct: bool = Field(description="True if the answer matches the reference answer's meaning.")
    reasoning: str = Field(description="One short sentence explaining the verdict.")


def llm_judge(run: Run, example: Example) -> dict:
    prompt = f"""Question: {example.inputs['question']}
Reference answer: {example.outputs['answer']}
Answer to grade: {run.outputs['answer']}

Does the answer to grade match the reference answer's meaning?"""
    verdict = llm.with_structured_output(Verdict).invoke(prompt)
    return {"key": "correctness", "score": int(verdict.correct), "comment": verdict.reasoning}


if __name__ == "__main__":
    results = evaluate(predict, data=DATASET_NAME, evaluators=[llm_judge], experiment_prefix="eval-dataset-demo")

    golden_passed = golden_total = edge_passed = edge_total = 0
    for row in results:
        category = row["example"].metadata["category"]
        score = row["evaluation_results"]["results"][0].score
        question = row["example"].inputs["question"]
        answer = row["run"].outputs["answer"]
        print(f"[{category}] {'PASS' if score else 'FAIL'} - {question!r} -> {answer!r}")
        if category == "golden":
            golden_total += 1
            golden_passed += bool(score)
        else:
            edge_total += 1
            edge_passed += bool(score)

    print(f"\nGolden QA pairs: {golden_passed}/{golden_total} correct")
    print(f"Edge cases:      {edge_passed}/{edge_total} correct")
