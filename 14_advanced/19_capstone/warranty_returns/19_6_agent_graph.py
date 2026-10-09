# pip install langgraph langgraph-checkpoint-sqlite langchain-openai mcp prometheus-client python-dotenv
import warnings
warnings.filterwarnings("ignore")
from capstone_common import quiet_langgraph_import
quiet_langgraph_import()

import asyncio
import json
import os
import re
import sqlite3
import sys
import threading
import time
import uuid
from contextlib import AsyncExitStack
from datetime import date
from typing import Literal, TypedDict

from dotenv import load_dotenv
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.errors import GraphInterrupt
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from prometheus_client import Counter, Histogram
from pydantic import BaseModel, Field

from capstone_common import (BASE_DIR, CHECKPOINT_DB, MAX_REVIEW_LOOPS, REFUND_APPROVAL_LIMIT,
                             REPAIR_PRICE_THRESHOLD, TICKETS_FILE, load_step, today)

load_dotenv(override=True)

rag = load_step("19_2_ingest_policies.py")      # retrieve(), get_clause()
guardrails = load_step("19_5_guardrails.py")    # check_input(), validate_output()

# =====================================================================
# STEP 6 of the capstone: the core agent loop.
# RAG + LangGraph + MCP tools + guardrails, running one ticket end-to-end.
#
#   input rails -> TRIAGE -> POLICY RESEARCHER  (RAG, 19_2) --+
#                        \-> ORDER INVESTIGATOR (MCP, 19_3) --+-> DECISION MAKER
#   -> RESOLUTION WRITER <-> REVIEWER (loop, max 2) -> OUTPUT VALIDATORS
#   -> [needs a human?] -> REQUEST APPROVAL (MCP, 19_4) -> APPROVAL GATE (interrupt)
#   -> FINALIZE
#
# Who uses what:
#   Triage, Writer, Reviewer   the LLM (gpt-4o-mini)
#   Policy Researcher          the RAG index - no LLM
#   Order Investigator         MCP tools - no LLM
#   Decision Maker             RULES applied to the retrieved clauses and the
#                              order facts - no LLM. Money decisions must be
#                              repeatable and explainable, so the LLM does the
#                              language work and the rules do the deciding.
#
# OFFLINE MODE: --offline (or no OPENAI_API_KEY) swaps the three LLM steps for
# simple keyword/template stand-ins. Everything else - retrieval, MCP calls,
# rules, guardrails, the approval interrupt - is exactly the same code, so the
# whole pipeline can be demonstrated without a network.
#
# TRACING: with LANGSMITH_TRACING=true in .env every ticket becomes one trace
# named "ticket-<id>", tagged with the mode; each node below is a span.
#
# Run it:
#   python 19_6_agent_graph.py                       ticket T01 (replacement, no approval)
#   python 19_6_agent_graph.py --ticket T03          high-value refund -> pauses for approval
#   python 19_6_agent_graph.py --ticket T03 --approve   (or --reject) answer without typing
#   python 19_6_agent_graph.py "My kettle from ORD-1011 does not heat"
#   add --offline to any of these to run without the LLM
# =====================================================================

OFFLINE = "--offline" in sys.argv or os.getenv("CAPSTONE_OFFLINE") == "1" or not os.getenv("OPENAI_API_KEY")
VERBOSE = False      # set by the command-line demo; the API and the test runner stay quiet

# ---------------------------------------------------------------- metrics
# Scraped by Prometheus through the /metrics endpoint of 19_7_api.py.
TICKETS_TOTAL = Counter("capstone_tickets_total", "Tickets finished, by final decision", ["decision"])
TICKET_SECONDS = Histogram("capstone_ticket_duration_seconds", "End-to-end time per ticket (excludes waiting for a human)",
                           buckets=(0.5, 1, 2, 5, 10, 15, 30, 60))
NODE_SECONDS = Histogram("capstone_node_duration_seconds", "Time spent in each graph node", ["node"],
                         buckets=(0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10))
LLM_TOKENS = Counter("capstone_llm_tokens_total", "LLM tokens used", ["kind"])
ERRORS_TOTAL = Counter("capstone_errors_total", "Failures by component", ["component"])
ESCALATIONS_TOTAL = Counter("capstone_escalations_total", "Tickets sent to a human approver")
GUARDRAIL_BLOCKS = Counter("capstone_guardrail_blocks_total", "Inputs blocked or outputs failed, by rail", ["rail"])
# Create the labelled series at 0 so dashboards show a line instead of "No data" before the first event.
for _kind in ("input", "output"):
    LLM_TOKENS.labels(kind=_kind)
for _component in ("llm", "api"):
    ERRORS_TOTAL.labels(component=_component)
for _rail in ("prompt_injection", "off_topic", "refund_limit", "citation_required", "pii", "false_promise"):
    GUARDRAIL_BLOCKS.labels(rail=_rail)


# ---------------------------------------------------------------- shared state
class TicketState(TypedDict, total=False):
    ticket_id: str
    message: str                 # customer text, already PII-scrubbed
    blocked_by: str              # input rail that stopped the ticket, if any
    pii_found: list[str]
    claim_type: str              # warranty | return | other
    order_id: str
    product_category: str
    wants_refund: bool
    damage: str                  # none | physical | liquid
    order: dict                  # from Order Investigator
    past_claims: list[dict]
    clauses: list[dict]          # from Policy Researcher
    decision: str                # refund | replacement | repair | reject | need_info | out_of_scope | blocked
    reason: str
    citations: list[str]         # clause ids the decision rests on
    refund_amount: float
    draft_reply: str
    review_feedback: str
    review_count: int
    needs_approval: bool
    approval_reason: str
    approved: bool
    approver_note: str
    final_reply: str
    status: str                  # resolved | referred_to_specialist


def node(name: str):
    """Wrap a node: time it for Prometheus and print a progress line in the demo."""
    def wrap(fn):
        def run(state: TicketState):
            started = time.perf_counter()
            try:
                update = fn(state)
            except GraphInterrupt:        # the approval gate pausing is not a failure
                raise
            except Exception:
                ERRORS_TOTAL.labels(component=name).inc()
                raise
            finally:
                NODE_SECONDS.labels(node=name).observe(time.perf_counter() - started)
            if VERBOSE:
                _show(name, update or {})
            return update
        run.__name__ = name
        return run
    return wrap


# ---------------------------------------------------------------- MCP tools
class MCPToolbox:
    """Keeps one stdio session open to each MCP server, on a background event loop,
    so the (synchronous) graph nodes can call tools with a plain function call."""
    SERVERS = {"orders": "19_3_mcp_orders_server.py", "notify": "19_4_mcp_notify_server.py"}

    def __init__(self):
        self._sessions: dict[str, ClientSession] = {}
        self._ready = threading.Event()
        self._error: Exception | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._stop: asyncio.Event | None = None
        threading.Thread(target=lambda: asyncio.run(self._serve()), daemon=True).start()
        self._ready.wait(60)
        if self._error or not self._sessions:
            raise RuntimeError(f"Could not start the MCP servers: {self._error}")

    async def _serve(self):
        self._loop = asyncio.get_running_loop()
        self._stop = asyncio.Event()
        try:
            async with AsyncExitStack() as stack:
                for name, script in self.SERVERS.items():
                    params = StdioServerParameters(command=sys.executable, args=[os.path.join(BASE_DIR, script)],
                                                   env=dict(os.environ))
                    read, write = await stack.enter_async_context(stdio_client(params))
                    session = await stack.enter_async_context(ClientSession(read, write))
                    await session.initialize()
                    self._sessions[name] = session
                self._ready.set()
                await self._stop.wait()
        except Exception as exc:      # surface startup failures to the caller thread
            self._error = exc
            self._ready.set()

    def call(self, server: str, tool: str, arguments: dict):
        future = asyncio.run_coroutine_threadsafe(self._sessions[server].call_tool(tool, arguments), self._loop)
        return json.loads(future.result(timeout=30).content[0].text)

    def close(self):
        if self._loop and self._stop:
            self._loop.call_soon_threadsafe(self._stop.set)


_toolbox: MCPToolbox | None = None


def toolbox() -> MCPToolbox:
    global _toolbox
    if _toolbox is None:
        _toolbox = MCPToolbox()
    return _toolbox


# ---------------------------------------------------------------- LLM helpers
_llm = None
_llm_down_until = 0.0      # circuit breaker: after a failure, skip the LLM for a minute


def llm():
    global _llm
    if _llm is None:
        from langchain_openai import ChatOpenAI
        _llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, timeout=30, max_retries=1)
    return _llm


def _count_tokens(message):
    usage = getattr(message, "usage_metadata", None) or {}
    LLM_TOKENS.labels(kind="input").inc(usage.get("input_tokens", 0))
    LLM_TOKENS.labels(kind="output").inc(usage.get("output_tokens", 0))


def ask_llm(prompt: str, schema=None, fallback=None):
    """Call the LLM (structured if a schema is given). In offline mode, or if the
    call fails, use the fallback function so a ticket is never lost to an outage."""
    global _llm_down_until
    if not OFFLINE and time.time() >= _llm_down_until:
        try:
            if schema is None:
                message = llm().invoke(prompt)
                _count_tokens(message)
                return message.content
            result = llm().with_structured_output(schema, include_raw=True).invoke(prompt)
            _count_tokens(result["raw"])
            return result["parsed"]
        except Exception as exc:
            ERRORS_TOTAL.labels(component="llm").inc()
            _llm_down_until = time.time() + 60
            print(f"  [warning] LLM call failed ({type(exc).__name__}); using the offline stand-ins for the next 60 seconds.")
    return fallback()


# ---------------------------------------------------------------- nodes
@node("input_rails")
def input_rails(state: TicketState):
    # The rails themselves ran in prepare_ticket(), BEFORE the graph started, so
    # that un-scrubbed text never reaches a checkpoint or a trace. This node only
    # acts on their verdict.
    if state.get("blocked_by"):
        GUARDRAIL_BLOCKS.labels(rail=state["blocked_by"]).inc()
        return {"decision": "blocked" if state["blocked_by"] == "prompt_injection" else "out_of_scope"}
    return {}


class Triage(BaseModel):
    claim_type: Literal["warranty", "return", "other"] = Field(
        description="warranty = product is faulty or damaged; return = customer wants to send back a working "
                    "product; other = anything else, such as a sales question")
    product_category: Literal["audio", "mobile", "laptop", "appliance", "accessory", "all"] = Field(
        description="audio = headphones/earbuds/speakers; appliance = mixer/kettle/iron; accessory = cable/"
                    "charger/case/power bank; all = not clear")
    wants_refund: bool = Field(description="True only if the customer explicitly asks for money back")
    damage: Literal["none", "physical", "liquid"] = Field(
        description="physical = dropped/cracked/dented; liquid = water or any liquid spilled; else none")


DEFECT_WORDS = ["not working", "stopped", "not charging", "does not charge", "no sound", "fault", "defect",
                "drain", "does not switch on", "does not start", "does not heat", "cracked", "spill", "broken"]
RETURN_WORDS = ["return", "take back", "changed my mind", "by mistake", "do not need", "don't need"]
CATEGORY_WORDS = [("accessory", ["power bank", "cable", "usb", "charger case"]), ("laptop", ["laptop"]),
                  ("audio", ["headphone", "earbud", "earphone", "speaker"]),
                  ("appliance", ["mixer", "grinder", "kettle", "iron"]), ("mobile", ["phone", "smartphone"])]


def _triage_offline(text: str) -> Triage:
    low = text.lower()
    defect = any(w in low for w in DEFECT_WORDS)
    claim = "warranty" if defect else "return" if any(w in low for w in RETURN_WORDS) else "other"
    category = next((cat for cat, words in CATEGORY_WORDS if any(w in low for w in words)), "all")
    damage = ("liquid" if any(w in low for w in ["spill", "water", "liquid", "wet"]) else
              "physical" if any(w in low for w in ["dropped", "cracked", "fell", "dent"]) else "none")
    return Triage(claim_type=claim, product_category=category, wants_refund="refund" in low, damage=damage)


@node("triage")
def triage(state: TicketState):
    text = state["message"]
    result = ask_llm("You are the triage agent of an electronics retailer's support desk. "
                     f"Classify this customer message.\n\nMessage: {text}",
                     schema=Triage, fallback=lambda: _triage_offline(text))
    # The order id is extracted with a pattern, never by the LLM: an id must be exact.
    found = re.search(r"ORD-\d{4}", text.upper())
    update = {"claim_type": result.claim_type, "product_category": result.product_category,
              "wants_refund": result.wants_refund, "damage": result.damage,
              "order_id": found.group(0) if found else ""}
    if result.claim_type == "other":
        update["decision"] = "out_of_scope"      # routed straight to finalize
    return update


@node("policy_researcher")
def policy_researcher(state: TicketState):
    category = state["product_category"]
    if state["claim_type"] == "warranty":
        queries = [(state["message"], None),
                   (f"{category} warranty period months from delivery", ["warranty_policy"]),
                   ("remedy for a covered defect: refund, replacement or repair", ["warranty_policy"]),
                   ("damage that is not covered by the warranty", ["warranty_policy"])]
    else:
        queries = [(state["message"], None),
                   ("return window: how many days after delivery", ["returns_policy"]),
                   ("refund for an accepted return", ["returns_policy", "refund_policy"])]
    clauses: dict[str, dict] = {}
    for query, doc_types in queries:
        for hit in rag.retrieve(query, product_category=category, doc_types=doc_types, k=3):
            clauses.setdefault(hit["id"], hit)
    return {"clauses": list(clauses.values())}


@node("order_investigator")
def order_investigator(state: TicketState):
    if not state.get("order_id"):
        return {"order": {}, "past_claims": []}
    order = toolbox().call("orders", "get_order", {"order_id": state["order_id"]})
    if "error" in order:
        return {"order": order, "past_claims": []}
    return {"order": order,
            "past_claims": toolbox().call("orders", "get_past_claims", {"order_id": state["order_id"]})}


def _add_months(start: date, months: int) -> date:
    year, month = divmod(start.month - 1 + months, 12)
    year, month = start.year + year, month + 1
    last_day = [31, 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28,
                31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1]
    return date(year, month, min(start.day, last_day))


def _first_number(text: str, pattern: str) -> int:
    return int(re.search(pattern, text).group(1))


@node("decision_maker")
def decision_maker(state: TicketState):
    clauses = {c["id"]: c for c in state.get("clauses", [])}
    citations: list[str] = []

    def cite(doc_name: str, section: str) -> dict:
        """Use a clause as a reason. If the researcher's search did not bring it
        back, fetch that exact clause - a decision may only rest on real text."""
        clause_id = f"{doc_name}:{section}"
        if clause_id not in clauses:
            clauses[clause_id] = rag.get_clause(doc_name, section)
        if clause_id not in citations:
            citations.append(clause_id)
        return clauses[clause_id]

    def done(decision, reason, refund=0.0, approval_reason=""):
        return {"decision": decision, "reason": reason, "refund_amount": float(refund), "citations": citations,
                "clauses": list(clauses.values()), "needs_approval": bool(approval_reason),
                "approval_reason": approval_reason}

    order = state.get("order") or {}
    if not state.get("order_id"):
        return done("need_info", "The message does not contain an order id.")
    if "error" in order:
        return done("need_info", f"Order {state['order_id']} was not found.")

    price, category = order["price"], order["category"]
    delivered = date.fromisoformat(order["delivery_date"])
    days = (today() - delivered).days
    approval: list[str] = []

    if state["claim_type"] == "warranty":
        if state.get("damage") in ("physical", "liquid"):
            cite("Warranty_Policy", "7.1")
            decision, refund = "reject", 0
            reason = f"The fault was caused by {state['damage']} damage, which the warranty does not cover."
        else:
            period = next((c for c in clauses.values() if c["doc_type"] == "warranty_policy"
                           and c["product_category"] == category and "months" in c["text"]), None)
            if period is None:      # triage guessed another category; search again with the order's real one
                period = next(c for c in rag.retrieve(f"{category} warranty period months", category,
                                                      ["warranty_policy"], k=6)
                              if c["product_category"] == category and "months" in c["text"])
            months = _first_number(period["text"], r"(\d+) months")
            cite("Warranty_Policy", period["section"])
            if today() > _add_months(delivered, months):
                cite("Warranty_Policy", "8.3")
                decision, refund = "reject", 0
                reason = (f"The product was delivered {days} days ago and the {months}-month warranty for "
                          f"{category} products has ended.")
            else:
                early_days = _first_number(cite("Warranty_Policy", "8.1")["text"], r"within (\d+) days")
                if days <= early_days:
                    decision = "refund" if state.get("wants_refund") else "replacement"
                    refund = price if decision == "refund" else 0
                    reason = (f"A covered defect was reported {days} days after delivery, inside the "
                              f"{early_days}-day period in which the customer may choose a refund or a replacement.")
                else:
                    citations.remove("Warranty_Policy:8.1")
                    cite("Warranty_Policy", "8.2")
                    decision, refund = ("replacement" if price <= REPAIR_PRICE_THRESHOLD else "repair"), 0
                    reason = (f"A covered defect was reported {days} days after delivery, inside the {months}-month "
                              f"warranty. After {early_days} days a refund is not offered; a product priced at "
                              f"Rs. {price:,.0f} is {'replaced' if decision == 'replacement' else 'repaired free of charge'}.")
                if len(state.get("past_claims", [])) >= 2:
                    cite("Warranty_Policy", "8.4")
                    approval.append(f"{len(state['past_claims'])} earlier claims on this order")
    else:   # return
        if category == "accessory":
            cite("Returns_Policy", "1.2")
            decision, refund, reason = "reject", 0, "Accessories cannot be returned unless they are defective."
        else:
            window = _first_number(cite("Returns_Policy", "1.1")["text"], r"within (\d+) days")
            if days <= window:
                cite("Returns_Policy", "3.1")
                decision, refund = "refund", price
                reason = f"The return was requested {days} days after delivery, inside the {window}-day return window."
            else:
                citations.remove("Returns_Policy:1.1")
                cite("Returns_Policy", "4.1")
                decision, refund = "reject", 0
                reason = f"The return was requested {days} days after delivery, after the {window}-day return window."

    if decision == "refund" and refund > REFUND_APPROVAL_LIMIT:
        cite("Refund_and_Approval_Policy", "2.1")
        approval.append(f"refund of Rs. {refund:,.0f} is above the Rs. {REFUND_APPROVAL_LIMIT:,} limit")
    if decision == "reject":
        cite("Refund_and_Approval_Policy", "2.2")
        approval.append("rejections must be reviewed")
    return done(decision, reason, refund, "; ".join(approval))


def _citation_text(state: TicketState) -> str:
    by_id = {c["id"]: c for c in state["clauses"]}
    # Approval clauses are internal process; the customer is shown the clauses that explain the outcome.
    shown = [i for i in state["citations"] if not i.startswith("Refund_and_Approval_Policy")]
    return ", ".join(by_id[i]["citation"] for i in shown)


def _write_offline(state: TicketState) -> str:
    order, decision = state["order"], state["decision"]
    outcome = {
        "refund": f"we will refund Rs. {state['refund_amount']:,.0f} to your original payment method",
        "replacement": "we will replace the product at no cost to you",
        "repair": "we will repair the product free of charge at an authorised service centre",
        "reject": "we are unable to accept this request",
    }[decision]
    return (f"Dear {order['customer_name'].split()[0]},\n\n"
            f"Thank you for contacting ElectroMart about your {order['product_name']} (order {order['order_id']}). "
            f"{state['reason']} As a result, {outcome}.\n\n"
            f"This decision is based on: {_citation_text(state)}.\n\n"
            f"Regards,\nElectroMart Support")


@node("resolution_writer")
def resolution_writer(state: TicketState):
    by_id = {c["id"]: c for c in state["clauses"]}
    clause_text = "\n".join(f"- {by_id[i]['citation']}: {by_id[i]['text']}" for i in state["citations"])
    feedback = f"\nA reviewer rejected your previous draft. Fix this: {state['review_feedback']}" \
        if state.get("review_feedback") else ""
    prompt = (
        "You write replies for ElectroMart customer support. Write a short, polite reply to the customer.\n"
        "Rules: state the decision exactly as given - do not change it or offer anything else; explain the reason "
        "in plain words; name the policy clauses using the wording 'clause <number>' with the document name; "
        "do not mention internal approval; do not include phone numbers or e-mail addresses; "
        "only use the word 'refund' for something we will do if the decision is refund.\n\n"
        f"Customer first name: {state['order']['customer_name'].split()[0]}\n"
        f"Product: {state['order']['product_name']} (order {state['order']['order_id']})\n"
        f"Customer message: {state['message']}\n"
        f"Decision: {state['decision']}" + (f" of Rs. {state['refund_amount']:,.0f}" if state["refund_amount"] else "") + "\n"
        f"Reason: {state['reason']}\n"
        f"Clauses to cite: {_citation_text(state)}\n"
        f"Clause text:\n{clause_text}{feedback}")
    return {"draft_reply": ask_llm(prompt, fallback=lambda: _write_offline(state))}


class Review(BaseModel):
    approved: bool = Field(description="True if the reply can be sent as it is")
    feedback: str = Field(description="If not approved: one sentence saying what to fix. Otherwise empty.")


@node("reviewer")
def reviewer(state: TicketState):
    def offline():
        ok = "clause" in state["draft_reply"].lower() and state["order"]["order_id"] in state["draft_reply"]
        return Review(approved=ok, feedback="" if ok else "Name the order id and the policy clause.")
    review = ask_llm(
        "You review customer-support replies before they are sent. Approve the reply only if it states the "
        "decision correctly, gives the reason, names at least one policy clause, and is polite.\n\n"
        f"Decision that must be communicated: {state['decision']}\nReason: {state['reason']}\n"
        f"Clauses: {_citation_text(state)}\n\nReply to review:\n{state['draft_reply']}",
        schema=Review, fallback=offline)
    return {"review_feedback": "" if review.approved else review.feedback,
            "review_count": state.get("review_count", 0) + 1}


@node("output_validators")
def output_validators(state: TicketState):
    problems = guardrails.validate_output(
        state["decision"], state["refund_amount"], state["order"], state["citations"],
        [c["id"] for c in state["clauses"]], state["draft_reply"])
    for problem in problems:
        GUARDRAIL_BLOCKS.labels(rail=problem.split(":")[0]).inc()
    if not problems:
        return {"review_feedback": ""}
    if state.get("review_count", 0) < MAX_REVIEW_LOOPS:
        return {"review_feedback": "; ".join(problems)}          # back to the writer
    # Still failing after the allowed rewrites: a human must look at it.
    return {"review_feedback": "", "needs_approval": True,
            "approval_reason": "output validators failed: " + "; ".join(problems)}


@node("request_approval")
def request_approval(state: TicketState):
    ESCALATIONS_TOTAL.inc()
    toolbox().call("notify", "send_approval_request",
                   {"ticket_id": state["ticket_id"], "decision": state["decision"],
                    "amount": state["refund_amount"], "reason": state["approval_reason"]})
    return {}


@node("approval_gate")
def approval_gate(state: TicketState):
    # interrupt() pauses the graph here and checkpoints the state. The ticket can
    # wait for minutes or days; Command(resume=...) continues from this line.
    answer = interrupt({"ticket_id": state["ticket_id"], "decision": state["decision"],
                        "refund_amount": state["refund_amount"], "why_approval": state["approval_reason"],
                        "reason": state["reason"], "draft_reply": state["draft_reply"]})
    return {"approved": bool(answer.get("approved")), "approver_note": answer.get("note", "")}


@node("finalize")
def finalize(state: TicketState):
    decision = state["decision"]
    if decision == "blocked":
        reply = "We could not process this message. Please describe the problem with your order."
    elif decision == "out_of_scope":
        reply = ("We can help with warranty claims and returns for ElectroMart orders. "
                 "For anything else please visit the ElectroMart help centre.")
    elif decision == "need_info":
        reply = f"{state['reason']} Please send us your order id (for example ORD-1234) so we can look into it."
    elif state.get("needs_approval") and not state.get("approved"):
        TICKETS_TOTAL.labels(decision="referred_to_specialist").inc()
        return {"status": "referred_to_specialist",
                "final_reply": "Thank you for your patience. Your request needs a closer look and a support "
                               "specialist will contact you within one working day."}
    else:
        reply = state["draft_reply"]
    TICKETS_TOTAL.labels(decision=decision).inc()
    return {"status": "resolved", "final_reply": reply}


# ---------------------------------------------------------------- routing
def after_rails(state: TicketState):
    return "finalize" if state.get("blocked_by") else "triage"


def after_triage(state: TicketState):
    # Returning two node names runs both in parallel (task decomposition).
    return ["finalize"] if state["claim_type"] == "other" else ["policy_researcher", "order_investigator"]


def after_decision(state: TicketState):
    return "finalize" if state["decision"] == "need_info" else "resolution_writer"


def after_review(state: TicketState):
    if state.get("review_feedback") and state.get("review_count", 0) < MAX_REVIEW_LOOPS:
        return "resolution_writer"
    return "output_validators"


def after_validators(state: TicketState):
    if state.get("review_feedback"):
        return "resolution_writer"
    return "request_approval" if state.get("needs_approval") else "finalize"


def build_graph(checkpointer=None):
    graph = StateGraph(TicketState)
    for fn in (input_rails, triage, policy_researcher, order_investigator, decision_maker, resolution_writer,
               reviewer, output_validators, request_approval, approval_gate, finalize):
        graph.add_node(fn.__name__, fn)
    graph.add_edge(START, "input_rails")
    graph.add_conditional_edges("input_rails", after_rails, ["triage", "finalize"])
    graph.add_conditional_edges("triage", after_triage, ["policy_researcher", "order_investigator", "finalize"])
    graph.add_edge(["policy_researcher", "order_investigator"], "decision_maker")     # wait for both
    graph.add_conditional_edges("decision_maker", after_decision, ["resolution_writer", "finalize"])
    graph.add_edge("resolution_writer", "reviewer")
    graph.add_conditional_edges("reviewer", after_review, ["resolution_writer", "output_validators"])
    graph.add_conditional_edges("output_validators", after_validators,
                                ["resolution_writer", "request_approval", "finalize"])
    graph.add_edge("request_approval", "approval_gate")
    graph.add_edge("approval_gate", "finalize")
    graph.add_edge("finalize", END)
    if checkpointer is None:
        # SQLite, not memory: a ticket waiting for approval survives a restart.
        checkpointer = SqliteSaver(sqlite3.connect(CHECKPOINT_DB, check_same_thread=False))
    return graph.compile(checkpointer=checkpointer)


# ---------------------------------------------------------------- public helpers (used by 19_7 and 19_9)
def new_ticket_id() -> str:
    return "TKT-" + uuid.uuid4().hex[:6].upper()


def prepare_ticket(message: str, ticket_id: str | None = None) -> tuple[dict, dict]:
    """Run the input rails and build (initial_state, config) for the graph.
    Only the scrubbed message goes into the state."""
    ticket_id = ticket_id or new_ticket_id()
    rails = guardrails.check_input(message)
    state = {"ticket_id": ticket_id, "message": rails["clean_message"], "pii_found": rails["pii_found"],
             "blocked_by": rails["rail"] or "", "review_count": 0, "refund_amount": 0.0,
             "citations": [], "clauses": []}
    config = {"configurable": {"thread_id": ticket_id}, "run_name": f"ticket-{ticket_id}",
              "tags": ["capstone", "offline" if OFFLINE else "llm"], "metadata": {"ticket_id": ticket_id}}
    return state, config


def run_ticket(app, message: str, ticket_id: str | None = None) -> tuple[dict, dict]:
    """Run a ticket until it finishes or pauses for approval. Returns (result, config);
    result contains '__interrupt__' when a human is needed."""
    state, config = prepare_ticket(message, ticket_id)
    started = time.perf_counter()
    result = app.invoke(state, config)
    TICKET_SECONDS.observe(time.perf_counter() - started)
    return result, config


def resume_ticket(app, config: dict, approved: bool, note: str = "") -> dict:
    return app.invoke(Command(resume={"approved": approved, "note": note}), config)


# ---------------------------------------------------------------- command-line demo
def describe(name: str, update: dict) -> str:
    """One line saying what a node just did (used by the demo below and by the API's event stream)."""
    lines = {
        "input_rails": lambda u: "blocked" if u.get("decision") else "message allowed",
        "triage": lambda u: f"claim_type={u['claim_type']}, category={u['product_category']}, "
                            f"order_id={u['order_id'] or '(none)'}, wants_refund={u['wants_refund']}, damage={u['damage']}",
        "policy_researcher": lambda u: f"{len(u['clauses'])} clauses retrieved: " +
                                       ", ".join(c["citation"].replace(" clause ", " ") for c in u["clauses"][:6]) +
                                       (" ..." if len(u["clauses"]) > 6 else ""),
        "order_investigator": lambda u: (u["order"].get("error") or "no order id in the message") if not u["order"].get("price")
        else f"{u['order']['product_name']}, Rs. {u['order']['price']:,.0f}, delivered "
             f"{u['order']['delivery_date']}, {len(u['past_claims'])} past claim(s)",
        "decision_maker": lambda u: f"{u['decision'].upper()}" + (f" Rs. {u['refund_amount']:,.0f}" if u["refund_amount"] else "") +
                                    f" | cites {', '.join(u['citations']) or '-'}" +
                                    (f" | NEEDS APPROVAL: {u['approval_reason']}" if u["needs_approval"] else ""),
        "resolution_writer": lambda u: f"draft written ({len(u['draft_reply'])} characters)",
        "reviewer": lambda u: "approved" if not u["review_feedback"] else f"sent back: {u['review_feedback']}",
        "output_validators": lambda u: "all validators passed" if not u.get("review_feedback") and not u.get("needs_approval")
        else f"FAILED: {u.get('review_feedback') or u.get('approval_reason')}",
        "request_approval": lambda u: "approval request sent through the Notify MCP server",
        "approval_gate": lambda u: f"human answered: {'APPROVED' if u['approved'] else 'REJECTED'}",
        "finalize": lambda u: f"status={u['status']}",
    }
    return lines[name](update)


def _show(name: str, update: dict):
    print(f"  [{name:<18}] {describe(name, update)}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    VERBOSE = True
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if "--ticket" in sys.argv:
        wanted = sys.argv[sys.argv.index("--ticket") + 1]
        args = [a for a in args if a != wanted]
        with open(TICKETS_FILE, encoding="utf-8") as f:
            message = next(t["message"] for t in json.load(f) if t["id"] == wanted)
    else:
        message = " ".join(args) or "My SoundWave Pro headphones stopped charging after 5 months. Order ORD-1001. I want a refund."

    app = build_graph()
    print("=" * 78)
    print(f"MODE    : {'OFFLINE (keyword/template stand-ins for the LLM steps)' if OFFLINE else 'LLM (gpt-4o-mini)'}")
    print(f"TICKET  : {message}")
    print("=" * 78)
    result, config = run_ticket(app, message)

    if "__interrupt__" in result:
        pending = result["__interrupt__"][0].value
        print("\n" + "-" * 78)
        print("GRAPH PAUSED - waiting for a human approver")
        print(f"  Proposed : {pending['decision']}" + (f" of Rs. {pending['refund_amount']:,.0f}" if pending["refund_amount"] else ""))
        print(f"  Because  : {pending['why_approval']}")
        print("-" * 78)
        if "--approve" in sys.argv or "--reject" in sys.argv:
            approved = "--approve" in sys.argv
        else:
            approved = input("Approve this decision? (y/n): ").strip().lower().startswith("y")
        result = resume_ticket(app, config, approved, "decided from the command line")

    print("\n" + "=" * 78)
    print(f"FINAL   : decision={result['decision']}, status={result['status']}")
    print("=" * 78)
    print(result["final_reply"])
    if _toolbox:
        _toolbox.close()
