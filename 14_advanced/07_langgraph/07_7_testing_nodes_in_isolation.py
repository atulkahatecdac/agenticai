"""Testing a LangGraph graph piece by piece - no API key, no network.

Run either way, from 14_advanced/07_langgraph:
    python 07_7_testing_nodes_in_isolation.py      (runs pytest on this file)
    pytest -q 07_7_testing_nodes_in_isolation.py

The trick is in how the graph is written, not in the tests:
  * a node is a plain function: state in, partial update out
  * the LLM is passed in (build_graph(llm)), never created inside a node
  * the routing function is separate from the node that sets the label
So each piece can be called directly with a hand-made state and a fake LLM.
"""
import sys
from functools import partial
from typing import TypedDict

from langchain_core.language_models import BaseChatModel
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langgraph.graph import END, START, StateGraph

CATEGORIES = ("refund", "technical", "general")


class TicketState(TypedDict, total=False):
    message: str
    category: str
    reply: str
    escalate: bool


# ---------------------------------------------------------------------
# Nodes - plain functions. The LLM comes in as an argument.
# ---------------------------------------------------------------------
def classify(state: TicketState, llm: BaseChatModel) -> TicketState:
    label = llm.invoke(
        f"Reply with one word - {', '.join(CATEGORIES)} - for this ticket:\n{state['message']}"
    ).content.strip().lower().rstrip(".")
    return {"category": label if label in CATEGORIES else "general"}   # never trust the label blindly


def refund_desk(state: TicketState, llm: BaseChatModel) -> TicketState:
    reply = llm.invoke(f"Write a short, polite refund reply to: {state['message']}").content
    # Business rule, not LLM judgement: big amounts go to a human.
    return {"reply": reply, "escalate": "₹" in state["message"] and _amount(state["message"]) > 5000}


def tech_desk(state: TicketState, llm: BaseChatModel) -> TicketState:
    return {"reply": llm.invoke(f"Give one troubleshooting step for: {state['message']}").content, "escalate": False}


def general_desk(state: TicketState) -> TicketState:
    return {"reply": "Thanks for writing in - a colleague will reply within a day.", "escalate": False}


def _amount(text: str) -> int:
    digits = "".join(ch for ch in text.split("₹", 1)[1].split()[0] if ch.isdigit())
    return int(digits or 0)


# The routing function: reads state, returns the next node's name.
def route(state: TicketState) -> str:
    return {"refund": "refund_desk", "technical": "tech_desk"}.get(state["category"], "general_desk")


def build_graph(llm: BaseChatModel):
    g = StateGraph(TicketState)
    g.add_node("classify", partial(classify, llm=llm))
    g.add_node("refund_desk", partial(refund_desk, llm=llm))
    g.add_node("tech_desk", partial(tech_desk, llm=llm))
    g.add_node("general_desk", general_desk)
    g.add_edge(START, "classify")
    g.add_conditional_edges("classify", route, ["refund_desk", "tech_desk", "general_desk"])
    for desk in ("refund_desk", "tech_desk", "general_desk"):
        g.add_edge(desk, END)
    return g.compile()


def fake(*replies: str) -> FakeListChatModel:
    """A stand-in LLM that returns these replies in order."""
    return FakeListChatModel(responses=list(replies))


# =====================================================================
# 1. Unit tests: one node, a hand-made state, a fake LLM.
# =====================================================================
def test_classify_reads_the_llm_label():
    assert classify({"message": "I want my money back"}, fake("Refund.")) == {"category": "refund"}


def test_classify_falls_back_on_an_unexpected_label():
    assert classify({"message": "hello"}, fake("Billing")) == {"category": "general"}


def test_refund_desk_escalates_big_amounts():
    out = refund_desk({"message": "Refund ₹12,000 for my phone"}, fake("Sorry to hear that."))
    assert out["escalate"] is True


def test_refund_desk_keeps_small_amounts():
    assert refund_desk({"message": "Refund ₹800 please"}, fake("Sure."))["escalate"] is False


def test_general_desk_needs_no_llm():
    assert "colleague" in general_desk({"message": "hi"})["reply"]


# =====================================================================
# 2. Routing tests: just a dict in, a node name out - no LLM at all.
# =====================================================================
def test_route_every_category():
    assert route({"category": "refund"}) == "refund_desk"
    assert route({"category": "technical"}) == "tech_desk"
    assert route({"category": "general"}) == "general_desk"


# =====================================================================
# 3. One end-to-end test of the wiring: the fake LLM answers the
#    classifier first, then the desk - in the order the graph calls it.
# =====================================================================
def test_whole_graph_takes_the_technical_path():
    graph = build_graph(fake("technical", "Restart the router."))
    result = graph.invoke({"message": "My Wi-Fi keeps dropping"})
    assert result["category"] == "technical"
    assert result["reply"] == "Restart the router."
    assert result["escalate"] is False


def test_each_node_runs_once_in_order():
    graph = build_graph(fake("refund", "We will refund you."))
    steps = [list(chunk)[0] for chunk in graph.stream({"message": "Refund ₹999"}, stream_mode="updates")]
    assert steps == ["classify", "refund_desk"]


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main(["-v", "-p", "no:cacheprovider", __file__]))
