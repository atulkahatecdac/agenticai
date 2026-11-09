import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)
# Harmless pydantic warning triggered by with_structured_output() on every
# judge call below - pure noise, drowns out the actual demo output.
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")

import csv
import os
import sys
from dotenv import load_dotenv

load_dotenv(override=True)

# .env's LANGSMITH_PROJECT is shared with another exercise (a CrewAI
# demo) - use a dedicated project so this script's experiments don't mix in.
os.environ["LANGSMITH_PROJECT"] = "agenticai-09-langsmith-demo"

# LLM output can contain characters outside Windows' default console
# codepage (cp1252) - reconfigure stdout to UTF-8 so printing doesn't crash.
sys.stdout.reconfigure(encoding="utf-8")

from pydantic import BaseModel, Field
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langsmith import Client, evaluate
from langsmith.schemas import Example, Run

# =====================================================================
# Prompt regression testing with LangSmith: run TWO prompt versions
# over the SAME dataset with the SAME evaluator, as two separate
# experiments under one LangSmith dataset - so they show up side by
# side in LangSmith's compare view, the way you'd check a prompt change
# didn't quietly make answers worse before shipping it.
# =====================================================================

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
judge_llm = ChatOpenAI(model="gpt-4o", temperature=0)  # separate, stronger judge model

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, "..", "..", "3_langgraph", "Dataset_Banking_chatbot.csv")

with open(CSV_PATH, newline="", encoding="utf-8") as f:
    faq_rows = list(csv.DictReader(f))[:6]  # keep the demo small/cheap

# Small in-memory ChromaDB collection over the bank's FAQ questions, so
# prompt v2 below can retrieve the actual known-good answer as context.
vectorstore = Chroma.from_documents(
    [Document(page_content=row["Query"], metadata={"answer": row["Response"]}) for row in faq_rows],
    embedding=OpenAIEmbeddings(model="text-embedding-3-small"),
)

DATASET_NAME = "agenticai-09-langsmith-banking-regression-demo"
examples = [{"inputs": {"question": row["Query"]}, "outputs": {"answer": row["Response"]}} for row in faq_rows]

client = Client()
if client.has_dataset(dataset_name=DATASET_NAME):
    client.delete_dataset(dataset_name=DATASET_NAME)
client.create_dataset(DATASET_NAME)
client.create_examples(dataset_name=DATASET_NAME, examples=examples)


def predict_v1(inputs: dict) -> dict:
    # PROMPT V1 (baseline): answers from the model's own knowledge only.
    response = llm.invoke(f"Answer this bank customer's question briefly: {inputs['question']}")
    return {"answer": response.content}


def predict_v2(inputs: dict) -> dict:
    # PROMPT V2 (candidate): grounds the answer in the bank's own FAQ via retrieval.
    match = vectorstore.similarity_search(inputs["question"], k=1)[0]
    prompt = f"""Answer this bank customer's question briefly, using the reference FAQ answer below \
as the source of truth.

Reference FAQ answer: {match.metadata['answer']}
Customer question: {inputs['question']}"""
    response = llm.invoke(prompt)
    return {"answer": response.content}


class Verdict(BaseModel):
    correct: bool = Field(
        description="True only if the answer contains every concrete, checkable fact from the "
        "reference (phone numbers, specific requirements, named steps) - not just a plausible "
        "process that sounds similar. Generic advice that omits a specific fact the reference "
        "states is NOT correct, even if the overall gist is right."
    )
    reasoning: str = Field(description="One sentence explaining the verdict - name the specific fact that was matched or missing.")


def llm_judge(run: Run, example: Example) -> dict:
    # Deliberately strict: wording may vary, but every SPECIFIC fact in
    # the reference (a phone number, a required document, an exact step)
    # must actually be present. A looser rubric ("does this sound like a
    # reasonable answer") would pass a generic non-answer that quietly
    # dropped the one fact that mattered - which is exactly the kind of
    # regression this file exists to catch.
    prompt = f"""Grade this bank support answer against the reference answer. Wording may differ, \
but check whether every SPECIFIC, checkable fact in the reference (phone numbers, named \
documents, exact steps, dollar amounts) is actually present in the answer being graded. An \
answer that gives correct-sounding but GENERIC advice while omitting a specific fact the \
reference states should be marked incorrect.

Question: {example.inputs['question']}
Reference answer: {example.outputs['answer']}
Answer to grade: {run.outputs['answer']}"""
    verdict = judge_llm.with_structured_output(Verdict).invoke(prompt)
    return {"key": "correctness", "score": int(verdict.correct), "comment": verdict.reasoning}


if __name__ == "__main__":
    # Run both prompt versions first, keyed by question, so they can be
    # printed side by side below instead of as two disconnected blocks.
    runs_by_version = {}
    for name, predict_fn in [("prompt-v1-baseline", predict_v1), ("prompt-v2-rag", predict_v2)]:
        print(f"Running {name}...")
        results = evaluate(predict_fn, data=DATASET_NAME, evaluators=[llm_judge], experiment_prefix=name)
        runs_by_version[name] = {row["example"].inputs["question"]: row for row in results}

    print("\n" + "=" * 70)
    print("PROMPT COMPARISON: v1 (own knowledge) vs v2 (RAG-grounded)")
    print("=" * 70)

    v1_passed = v2_passed = 0
    for example in examples:
        question = example["inputs"]["question"]
        row_v1 = runs_by_version["prompt-v1-baseline"][question]
        row_v2 = runs_by_version["prompt-v2-rag"][question]
        verdict_v1 = row_v1["evaluation_results"]["results"][0]
        verdict_v2 = row_v2["evaluation_results"]["results"][0]
        v1_passed += bool(verdict_v1.score)
        v2_passed += bool(verdict_v2.score)

        print(f"\nQ: {question}")
        print(f"  reference: {example['outputs']['answer']}")
        print(f"  v1 [{'PASS' if verdict_v1.score else 'FAIL'}]: {row_v1['run'].outputs['answer']}")
        print(f"  v2 [{'PASS' if verdict_v2.score else 'FAIL'}]: {row_v2['run'].outputs['answer']}")

    print(f"\nv1 baseline: {v1_passed}/{len(examples)} correct")
    print(f"v2 RAG:      {v2_passed}/{len(examples)} correct")
