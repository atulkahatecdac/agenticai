from typing import TypedDict, List, Literal, cast
from pydantic import BaseModel
from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

from dotenv import load_dotenv
load_dotenv(override=True)

MAX_ITERATIONS = 3

# The question has checkable rules, so a first attempt often misses one
# and the evaluator sends it back round the loop.
QUESTION = (
    "Explain how LangGraph helps build agentic AI apps in exactly 3 bullet points, "
    "each under 20 words, mentioning state, conditional edges and checkpointing."
)

# -----------------------------
# 1. STATE = SCHEMA
# -----------------------------
class AgentState(TypedDict):
    question: str
    answer: str
    history: List[str]
    iterations: int
    decision: str  # "continue" or "stop"
    feedback: str  # what the evaluator wants fixed


# -----------------------------
# 2. LLM
# -----------------------------
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)


class Verdict(BaseModel):
    decision: Literal["continue", "stop"]
    feedback: str


evaluator_llm = llm.with_structured_output(Verdict)


# -----------------------------
# 3. NODES
# -----------------------------
def answer_node(state: AgentState) -> dict:
    """Generate the answer, or revise it using the evaluator's feedback"""
    prompt = f"""
    Question: {state['question']}
    Previous attempt: {state['answer'] or 'none'}
    Reviewer feedback: {state['feedback'] or 'none'}

    Write the answer, fixing everything the reviewer pointed out.
    """
    response = llm.invoke([HumanMessage(content=prompt)])
    iteration = state["iterations"] + 1

    print(f"\n--- Attempt {iteration} ---\n{response.content}")

    return {
        "answer": response.content,
        "history": state["history"] + [response.content],
        "iterations": iteration,
    }


def evaluate_node(state: AgentState) -> dict:
    """Check the answer against every rule in the question"""
    prompt = f"""
    Question: {state['question']}
    Current answer: {state['answer']}

    Check the answer strictly against every rule in the question: the number of
    bullet points, the word limit for each bullet (count the words), and each
    required term. Reply "stop" only if every rule is met; otherwise reply
    "continue" and say exactly which rules were broken.
    """
    verdict = cast(Verdict, evaluator_llm.invoke([HumanMessage(content=prompt)]))

    print(f"[evaluate] {verdict.decision}: {verdict.feedback}")

    return {
        "decision": verdict.decision,
        "feedback": verdict.feedback,
    }


# -----------------------------
# 4. CONDITIONAL LOGIC
# -----------------------------
def should_continue(state: AgentState) -> str:
    # Memory-aware transition: always give the loop an exit
    if state["iterations"] >= MAX_ITERATIONS:
        return "stop"

    return state["decision"]


# -----------------------------
# 5. GRAPH
# -----------------------------
builder = StateGraph(AgentState)

builder.add_node("answer", answer_node)
builder.add_node("evaluate", evaluate_node)

builder.add_edge(START, "answer")

builder.add_edge("answer", "evaluate")

builder.add_conditional_edges(
    "evaluate",
    should_continue,
    {
        "continue": "answer",   # LOOP
        "stop": END             # EXIT
    }
)

graph = builder.compile()


# -----------------------------
# 6. RUN
# -----------------------------
initial_state: AgentState = {
    "question": QUESTION,
    "answer": "",
    "history": [],
    "iterations": 0,
    "decision": "continue",
    "feedback": "",
}

result = graph.invoke(initial_state)

print(f"\nFINAL ANSWER (after {result['iterations']} attempt(s)):\n")
print(result["answer"])
