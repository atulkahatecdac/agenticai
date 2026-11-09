import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

import os
import sys
from dotenv import load_dotenv

load_dotenv(override=True)

# .env's LANGSMITH_PROJECT is shared with another exercise (a CrewAI
# demo) - use a dedicated project so this script's experiment doesn't mix in.
os.environ["LANGSMITH_PROJECT"] = "agenticai-09-langsmith-demo"

# LLM output can contain characters outside Windows' default console
# codepage (cp1252) - reconfigure stdout to UTF-8 so printing doesn't crash.
sys.stdout.reconfigure(encoding="utf-8")

from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langsmith import Client, evaluate
from langsmith.schemas import Example, Run

# =====================================================================
# LangSmith as an LLM-as-a-judge evaluator.
#
# The scenario: grading a customer-support assistant's answers against
# the company's actual policy - one of the most common real production
# uses of LLM-as-judge (support/RAG bot QA), not an academic quiz. A
# policy answer can be phrased many correct ways ("30 days" vs "within
# a month of purchase"), so exact/fuzzy string matching would flag
# genuinely correct answers as wrong. evaluate() runs `predict` (the
# support bot) over each example, then hands every (run, example) pair
# to `llm_judge` - a SECOND LLM call that grades the bot's answer
# against the reference policy for a human support lead.
#
# The judge is deliberately a DIFFERENT, stronger model than the one
# being evaluated - grading a model with itself risks self-preference
# bias (rating its own phrasing/reasoning style more favorably) and
# means the judge shares the same blind spots as the thing it's
# checking. A stronger judge is more likely to actually catch the
# weaker model's mistakes instead of just rationalizing them.
#
# The messages below are written like real customer messages (messy,
# some irrelevant detail, sometimes requiring date math or judgment
# about whether a policy actually applies) rather than clean one-line
# trivia questions - including one that should be DENIED (a refund
# request 17 days after a 14-day window) and one not covered by policy
# at all, so there's a real chance to get it wrong, not just a rubber
# stamp.
# =====================================================================

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)  # system under test: the support bot
judge_llm = ChatOpenAI(model="gpt-4o", temperature=0)  # judge - stronger, separate model

# evaluate() needs a real LangSmith dataset (not a plain in-memory
# list) - recreated fresh on every run so edits to `examples` above
# always take effect, instead of silently evaluating against stale data.
DATASET_NAME = "agenticai-09-langsmith-qa-demo"
examples = [
    {
        "inputs": {"question": "Hey, I ordered 2 desk lamps last week (order #48213) and it's been like 9 business days and nothing's shipped yet, I'm getting kind of annoyed, what's going on??"},
        "outputs": {"answer": "Since it's been more than 7 business days without shipping, you're entitled to a free expedited reshipment or a full refund - sorry for the delay."},
    },
    {
        "inputs": {"question": "So I bought this jacket like 3 weeks ago, tried it on twice, still has tags on it, but I just don't think it fits right. Can I send it back?"},
        "outputs": {"answer": "Yes - since it's been less than 30 days and the item is unused with tags still attached, you can return it for a full refund."},
    },
    {
        "inputs": {"question": "We're a small business looking to place a recurring order of about 60 units every month - does that qualify for any pricing breaks, and is it a one-time discount or does it apply every time?"},
        "outputs": {"answer": "Yes - each order of 50 or more units qualifies for a 10% discount, so your recurring 60-unit orders would qualify every time; reach out to sales for a custom recurring quote."},
    },
    {
        "inputs": {"question": "My card got charged $49.99 out of nowhere on the 3rd, I think it's my old streaming plan renewing? I stopped using it months ago and completely forgot to cancel. Can you refund me, it's now the 20th."},
        "outputs": {"answer": "Unfortunately this charge is now 17 days old, past the 14-day window for accidental-renewal refunds, so we're unable to refund it this time - but you can cancel now to prevent future charges."},
    },
    {
        "inputs": {"question": "Also do you guys price match with Amazon? Saw the same lamp $10 cheaper there."},
        "outputs": {"answer": "We don't currently offer price matching, but thanks for letting us know - I'll pass the feedback along."},
    },
    {
        # Designed to trip the bot up: it's within the 30-day window, but
        # the policy also requires the item to be UNUSED - a model that
        # only pattern-matches on "within 30 days" and skips that second
        # condition will wrongly approve this one.
        "inputs": {"question": "I bought a blender 10 days ago and have used it a few times to make smoothies, but it's not blending as well as I hoped. Can I return it for a refund?"},
        "outputs": {"answer": "Unfortunately no - our return policy only covers unused items in original packaging, and since you've already used the blender, it doesn't qualify for a return."},
    },
]

client = Client()
if client.has_dataset(dataset_name=DATASET_NAME):
    client.delete_dataset(dataset_name=DATASET_NAME)
client.create_dataset(DATASET_NAME)
client.create_examples(dataset_name=DATASET_NAME, examples=examples)


# The bot answers grounded in an actual policy doc (like a real RAG
# support bot would) rather than guessing - without this it just gives
# vague, hedged non-answers with no policy specifics to grade at all.
COMPANY_POLICY = """\
Returns: Unused items in original packaging can be returned within 30 days of purchase for a full refund.
Shipping delays: If an order hasn't shipped within 7 business days, the customer is entitled to a free \
expedited reshipment or a full refund.
Bulk orders: Orders of 50 or more units qualify for a 10% discount; direct the customer to sales for a custom quote.
Subscription renewals: Accidental renewal charges are refundable within 14 days of the renewal charge, \
provided the customer hasn't used the service since renewing."""


def predict(inputs: dict) -> dict:
    prompt = f"""You are a customer support assistant. Using ONLY the company policy below, answer \
the customer's question.

Company policy:
{COMPANY_POLICY}

Customer question: {inputs['question']}"""
    response = llm.invoke(prompt)
    return {"answer": response.content}


class Verdict(BaseModel):
    score: int = Field(description="Quality score from 0 (completely wrong/unhelpful) to 10 (fully correct and matches policy exactly).", ge=0, le=10)
    correct: bool = Field(description="True if the support answer matches the reference policy, even if worded differently.")
    reasoning: str = Field(description="One sentence explaining the verdict.")


def llm_judge(run: Run, example: Example) -> dict:
    prompt = f"""You are a support-team lead reviewing a support bot's answer against actual \
company policy. Minor wording differences are fine as long as the policy (refund window, \
discount threshold, etc.) matches exactly - a wrong number or missing condition should be marked incorrect.

Customer question: {example.inputs['question']}
Reference policy answer: {example.outputs['answer']}
Bot's answer: {run.outputs['answer']}"""
    verdict = judge_llm.with_structured_output(Verdict).invoke(prompt)
    # One judge call, two feedback keys - a coarse pass/fail plus a
    # graded quality score, without a second LLM call.
    return {
        "results": [
            {"key": "policy_correctness", "score": int(verdict.correct), "comment": verdict.reasoning},
            {"key": "quality_score", "score": verdict.score, "comment": verdict.reasoning},
        ]
    }


if __name__ == "__main__":
    results = evaluate(
        predict,
        data=DATASET_NAME,
        evaluators=[llm_judge],
        experiment_prefix="llm-as-judge-demo",
    )

    for row in results:
        question = row["example"].inputs["question"]
        answer = row["run"].outputs["answer"]
        print(f"Q: {question}\nA: {answer}")
        for eval_result in row["evaluation_results"]["results"]:
            print(f"  {eval_result.key}: {eval_result.score} - {eval_result.comment}")
        print()
