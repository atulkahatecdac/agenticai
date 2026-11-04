from typing import TypedDict, List
from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

from dotenv import load_dotenv
load_dotenv(override=True)

# -----------------------------
# 1. STATE = SCHEMA
# -----------------------------
class AgentState(TypedDict):
    question: str
    answer: str
    history: List[str]
    iterations: int
    decision: str  # "continue" or "stop"


# -----------------------------
# 2. LLM
# -----------------------------
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)


# -----------------------------
# 3. NODES
# -----------------------------
def answer_node(state: AgentState) -> AgentState:
    """Generate or refine the answer"""
    prompt = f"""
    Question: {state['question']}
    Previous attempts: {state['history']}

    Improve the answer if needed.
    """
    response = llm.invoke([HumanMessage(content=prompt)])

    return {
        "answer": response.content,
        "history": state["history"] + [response.content],
        "iterations": state["iterations"] + 1,
    }


def evaluate_node(state: AgentState) -> AgentState:
    """Decide whether to stop or continue"""
    prompt = f"""
    Question: {state['question']}
    Current answer: {state['answer']}

    Is this answer complete and correct?
    Reply with only one word: continue or stop
    """
    response = llm.invoke([HumanMessage(content=prompt)])

    decision = "stop" if "stop" in response.content.lower() else "continue"

    return {
        "decision": decision
    }


# -----------------------------
# 4. CONDITIONAL LOGIC
# -----------------------------
def should_continue(state: AgentState) -> str:
    # Memory-aware transition
    if state["iterations"] >= 3:
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
initial_state = {
    "question": "Explain how LangGraph helps build Agentic AI apps",
    "answer": "",
    "history": [],
    "iterations": 0,
    "decision": "continue",
}

result = graph.invoke(initial_state)

print("\nFINAL ANSWER:\n")
print(result["answer"])
