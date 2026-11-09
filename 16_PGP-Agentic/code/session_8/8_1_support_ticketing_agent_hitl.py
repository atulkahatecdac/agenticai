import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

import os
import csv
import sys
from typing import TypedDict
import chromadb
from openai import OpenAI
from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command, interrupt

load_dotenv(override=True)
sys.stdout.reconfigure(encoding="utf-8")  # LLM output can include non-cp1252 characters

# =====================================================================
# RAG-based support ticket agent with a human-approval gate.
#
# Flow: triage_ticket (retrieve FAQs -> generate a draft reply -> decide
# auto-send or escalate) -> [human_approval if escalated] -> finalize.
#
# human_approval calls interrupt(), which PAUSES the graph and hands its
# payload back to the caller. A human then approves/edits/escalates via
# real console input(), and the graph resumes with
# app.invoke(Command(resume=...), config). Same pattern as
# 14_advanced/08_langgraph_cycles_HIL_persistence/human_approval_gate.py.
# =====================================================================

CSV_PATH = os.path.join(os.path.dirname(__file__), "customer_support_qa_500.csv")
MODEL = "gpt-4o-mini"
TOP_K = 3
MATCH_THRESHOLD = 0.4  # min cosine similarity to trust a retrieval enough to auto-send

# Requests tied to money or irreversible account actions always need a human.
SENSITIVE_KEYWORDS = ["refund", "cancel", "chargeback", "dispute", "compensation", "delete my account"]

openai_client = OpenAI()


def load_faq_index(csv_path: str):
    """Read the FAQ CSV and embed it into an in-memory ChromaDB collection."""
    with open(csv_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    collection = chromadb.Client().create_collection("support_faq", metadata={"hnsw:space": "cosine"})
    collection.add(
        ids=[row["id"] for row in rows],
        documents=[row["question"] for row in rows],
        metadatas=[{"answer": row["answer"]} for row in rows],
    )
    return collection


FAQ_INDEX = load_faq_index(CSV_PATH)


def retrieve(message: str) -> tuple[list[dict], float]:
    """Semantic search for the most relevant FAQs. Returns (matches, top similarity)."""
    result = FAQ_INDEX.query(query_texts=[message], n_results=TOP_K)
    matches = [
        {"question": q, "answer": meta["answer"]}
        for q, meta in zip(result["documents"][0], result["metadatas"][0])
    ]
    top_similarity = 1 - result["distances"][0][0]  # cosine distance -> similarity
    return matches, top_similarity


def generate(message: str, faqs: list[dict]) -> str:
    """Draft a reply grounded only in the retrieved FAQs - the 'G' in RAG."""
    context = "\n\n".join(f"Q: {faq['question']}\nA: {faq['answer']}" for faq in faqs)
    response = openai_client.responses.create(
        model=MODEL,
        instructions=(
            "You are a customer support assistant. Answer using ONLY the FAQ context below - "
            "do not invent policies. Keep it short. If the context doesn't answer the "
            "question, say a support agent will need to follow up."
        ),
        input=f"FAQ context:\n{context}\n\nCustomer message: {message}",
    )
    return response.output_text


def decide_routing(message: str, draft_response: str, similarity: float) -> tuple[str, str, list[str]]:
    """Auto-send only if the request is routine, safe, and the draft actually answers it.

    Returns (auto_decision, auto_reason, reasoning_steps) - reasoning_steps is the same
    checklist shown to the human reviewer, so the routing logic and the "why" they see
    can never drift apart into two different explanations of the same decision.
    """
    is_sensitive = any(keyword in message.lower() for keyword in SENSITIVE_KEYWORDS)
    looks_unanswered = "follow up" in draft_response.lower()
    is_confident = similarity >= MATCH_THRESHOLD

    steps = [
        f"{'[risk]' if is_sensitive else '[ok]'} Sensitive request (refund/cancel/delete): {'yes' if is_sensitive else 'no'}",
        f"{'[risk]' if looks_unanswered else '[ok]'} Draft reply actually answers the question: {'no' if looks_unanswered else 'yes'}",
        f"{'[ok]' if is_confident else '[risk]'} Retrieval confidence {similarity:.0%} "
        f"{'meets' if is_confident else 'is below'} the {MATCH_THRESHOLD:.0%} auto-send threshold",
    ]

    if is_sensitive:
        return "needs_review", "Mentions a refund/cancellation/account-deletion request - requires human sign-off.", steps

    if looks_unanswered:
        # A confident-looking retrieval can still be the wrong FAQs; trust the
        # generation step's own admission over the raw similarity score.
        return "needs_review", "The draft reply couldn't actually answer the question.", steps

    if not is_confident:
        return "needs_review", f"Low retrieval confidence ({similarity:.0%}).", steps

    return "auto_resolved", f"Confident retrieval ({similarity:.0%}) on a routine question.", steps


class TicketState(TypedDict):
    ticket_id: str
    customer_name: str
    category: str
    message: str
    retrieved_evidence: list[str]
    confidence: float
    reasoning_steps: list[str]
    auto_decision: str
    auto_reason: str
    draft_response: str
    final_response: str
    final_status: str


# ---- Node 1: retrieve + generate + decide whether a human needs to see this ----
def triage_ticket(state: TicketState) -> TicketState:
    faqs, similarity = retrieve(state["message"])
    draft_response = generate(state["message"], faqs)
    auto_decision, auto_reason, reasoning_steps = decide_routing(state["message"], draft_response, similarity)

    return {
        "retrieved_evidence": [f"Q: {faq['question']}  A: {faq['answer']}" for faq in faqs],
        "confidence": similarity,
        "reasoning_steps": reasoning_steps,
        "auto_decision": auto_decision,
        "auto_reason": auto_reason,
        "draft_response": draft_response,
    }


def route_after_triage(state: TicketState) -> str:
    return "human_approval" if state["auto_decision"] == "needs_review" else "finalize"


# ---- Node 2: the interrupt point - only reached for escalated tickets ----
def human_approval(state: TicketState) -> TicketState:
    decision = interrupt({
        "ticket_id": state["ticket_id"],
        "customer_name": state["customer_name"],
        "customer_message": state["message"],
        "recommendation": state["draft_response"],
        "confidence": state["confidence"],
        "evidence": state["retrieved_evidence"],
        "reasoning_steps": state["reasoning_steps"],
        "why_escalated": state["auto_reason"],
    })
    return {"final_status": decision["status"], "final_response": decision["response"]}


# ---- Node 3: fill in the final response for auto-resolved tickets ----
def finalize(state: TicketState) -> TicketState:
    if state["auto_decision"] == "auto_resolved":
        return {"final_status": "auto_resolved", "final_response": state["draft_response"]}
    return {}


# Graph: START -> triage_ticket --needs_review--> human_approval -> finalize -> END
#                        \_______________auto_resolved_______________/^
graph = StateGraph(TicketState)
graph.add_node("triage_ticket", triage_ticket)
graph.add_node("human_approval", human_approval)
graph.add_node("finalize", finalize)

graph.add_edge(START, "triage_ticket")
graph.add_conditional_edges(
    "triage_ticket", route_after_triage, {"human_approval": "human_approval", "finalize": "finalize"}
)
graph.add_edge("human_approval", "finalize")
graph.add_edge("finalize", END)

# Required for interrupt()/Command(resume=...) - lets the graph "remember" where it
# paused. MemorySaver only persists in-process; a real desk would use a DB-backed one.
app = graph.compile(checkpointer=MemorySaver())


def confidence_label(score: float) -> str:
    if score >= 0.7:
        return "High"
    if score >= MATCH_THRESHOLD:
        return "Medium"
    return "Low"


def render_review_card(pending: dict):
    """A good HITL review presents: a clear recommendation, supporting evidence, a
    confidence score, the retrieved documents behind that evidence, a reasoning
    summary explaining why a human is even seeing this, and clear action buttons -
    not a raw dump of internal field names and values."""
    width = 72
    print("\n" + "=" * width)
    print(" HUMAN REVIEW NEEDED ".center(width, "="))
    print("=" * width)
    print(f"Ticket {pending['ticket_id']} - {pending['customer_name']}")
    print(f'Customer message: "{pending["customer_message"]}"')

    print("-" * width)
    print("AI RECOMMENDATION")
    print(f"  {pending['recommendation']}")

    print("-" * width)
    print(f"CONFIDENCE SCORE   {pending['confidence']:.0%}  ({confidence_label(pending['confidence'])})")

    print("-" * width)
    print("SUPPORTING EVIDENCE (retrieved documents)")
    if pending["evidence"]:
        for i, item in enumerate(pending["evidence"], start=1):
            print(f"  [{i}] {item}")
    else:
        print("  (no relevant FAQ entries were retrieved)")

    print("-" * width)
    print("REASONING SUMMARY")
    for step in pending["reasoning_steps"]:
        print(f"  {step}")
    print(f"  => {pending['why_escalated']}")

    print("-" * width)
    print("ACTION:   [A] Approve the recommendation as-is")
    print("          [E] Edit before sending")
    print("          [X] Escalate to a senior agent")
    print("=" * width)


def ask_human_for_decision(pending: dict) -> dict:
    render_review_card(pending)

    while True:
        choice = input("Your decision [A/E/X]: ").strip().lower()
        if choice in ("a", "approve"):
            choice = "approve"
            break
        if choice in ("e", "edit"):
            choice = "edit"
            break
        if choice in ("x", "escalate"):
            choice = "escalate"
            break
        print("Please enter A (approve), E (edit), or X (escalate).")

    if choice == "approve":
        return {"status": "approved", "response": pending["recommendation"]}
    if choice == "edit":
        return {"status": "edited", "response": input("Enter the corrected response to send: ").strip()}
    return {"status": "escalated", "response": "Ticket escalated to a senior support agent."}


def run_ticket(ticket: dict) -> dict:
    config = {"configurable": {"thread_id": ticket["ticket_id"]}}
    initial: TicketState = {
        "retrieved_evidence": [],
        "confidence": 0.0,
        "reasoning_steps": [],
        "auto_decision": "",
        "auto_reason": "",
        "draft_response": "",
        "final_response": "",
        "final_status": "",
        **ticket,
    }

    result = app.invoke(initial, config)

    if "__interrupt__" in result:
        pending = result["__interrupt__"][0].value
        result = app.invoke(Command(resume=ask_human_for_decision(pending)), config)

    return result


if __name__ == "__main__":
    tickets = [
        {
            "ticket_id": "ticket-1",
            "customer_name": "Priya Sharma",
            "category": "Account",
            "message": "I forgot my password, how do I reset it?",
        },  # confident FAQ match, routine - auto-resolved, no human involved
        {
            "ticket_id": "ticket-2",
            "customer_name": "Sam Reyes",
            "category": "Billing",
            "message": "My payment was declined but I want a refund for the failed order anyway.",
        },  # mentions "refund" - pauses for a real human decision
        {
            "ticket_id": "ticket-3",
            "customer_name": "Jordan Lee",
            "category": "Technical",
            "message": "The app keeps making a weird noise and my screen flickers blue.",
        },  # no FAQ actually covers this - pauses for a real human decision
    ]

    for ticket in tickets:
        print("=" * 70)
        print(f"Processing {ticket['ticket_id']}: {ticket['customer_name']} ({ticket['category']})")
        print(f"Customer message: {ticket['message']}")

        result = run_ticket(ticket)

        print(f"Decision: {result['final_status'].upper()} - {result['auto_reason']}")
        print(f"Response sent: {result['final_response']}")
        print()
