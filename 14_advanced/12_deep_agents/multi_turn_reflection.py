import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")

import sys
from typing import TypedDict
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END

load_dotenv(override=True)
sys.stdout.reconfigure(encoding="utf-8")

# =====================================================================
# Multi-turn reflection: generate -> critique -> (revise or stop),
# looping until a quality judge's score clears THRESHOLD or
# MAX_ITERATIONS is hit (a real termination guarantee, not just a hope
# the model converges). Real product copywriting task, real LLM calls
# on both sides - no mocked scores or canned drafts.
# =====================================================================

THRESHOLD = 9
MAX_ITERATIONS = 4

writer_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)
judge_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)


class ReflectionState(TypedDict):
    task: str
    draft: str
    feedback: str
    score: int
    iteration: int


def generate(state: ReflectionState) -> ReflectionState:
    if state["draft"]:
        prompt = f"""Revise this product description using the feedback below. Output only the
revised description, nothing else.

Task: {state['task']}
Previous draft: {state['draft']}
Feedback: {state['feedback']}"""
    else:
        prompt = f"""Write a quick first-pass product description for this task - don't worry about
polish yet, a later revision pass will refine it. Output only the description, nothing else.

{state['task']}"""
    response = writer_llm.invoke(prompt)
    return {"draft": response.content, "iteration": state["iteration"] + 1}


class Critique(BaseModel):
    score: int = Field(description="Quality score 1-10 for clarity, persuasiveness, and conciseness.")
    feedback: str = Field(description="Specific, actionable feedback for improving the draft.")


def critique(state: ReflectionState) -> ReflectionState:
    prompt = f"""Grade this product description 1-10. Be strict - only score 9+ if ALL of these hold:
- Names at least one concrete, specific feature or spec (not just vague praise)
- Ties a benefit directly to the stated audience (busy, frequently-travelling professionals)
- Ends with a clear hook or call-to-action
- Reads as genuinely polished, ready-to-publish copy, not a rough draft

Task: {state['task']}
Draft: {state['draft']}"""
    verdict = judge_llm.with_structured_output(Critique).invoke(prompt)
    print(f"[iteration {state['iteration']}] score={verdict.score}/10 - {verdict.feedback}")
    return {"score": verdict.score, "feedback": verdict.feedback}


def should_continue(state: ReflectionState) -> str:
    if state["score"] >= THRESHOLD or state["iteration"] >= MAX_ITERATIONS:
        return "done"
    return "revise"


graph = StateGraph(ReflectionState)
graph.add_node("generate", generate)
graph.add_node("critique", critique)
graph.add_edge(START, "generate")
graph.add_edge("generate", "critique")
graph.add_conditional_edges("critique", should_continue, {"revise": "generate", "done": END})

app = graph.compile()

if __name__ == "__main__":
    task = ("Write a compelling 2-3 sentence product description for the Sony WH-1000XM5 wireless "
             "noise-cancelling headphones, aimed at busy professionals who travel frequently.")
    result = app.invoke({"task": task, "draft": "", "feedback": "", "score": 0, "iteration": 0})

    print(f"\n=== FINAL DRAFT (after {result['iteration']} iteration(s), score {result['score']}/10) ===")
    print(result["draft"])
