import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

import json
import os
import re
import sys
from io import BytesIO
from typing import Dict, List, TypedDict

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from fastapi import FastAPI, HTTPException, Request
from starlette.datastructures import UploadFile
from pypdf import PdfReader
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import create_react_agent

load_dotenv(override=True)

# LLM output can contain characters outside Windows' default console
# codepage (cp1252) - reconfigure stdout to UTF-8 so printing doesn't crash.
sys.stdout.reconfigure(encoding="utf-8")

# =====================================================================
# Insurance claim triage agent, exposed over HTTP so the n8n workflow in
# this folder (14_1_n8n_langgraph.json) can hand a claim off to LangGraph
# instead of doing the decisioning in n8n Code nodes. n8n's HTTP Request
# node posts the claim's PDF attachments straight through as
# multipart/form-data (whatever binary fields it has - "police_report",
# "accident_pdf", "attachment_3", ...; field names don't matter, this
# endpoint just takes every uploaded file). It does NOT send claim_id,
# customer_id or policy_number - by the time this is called, n8n's own
# Baserow nodes have already looked up the customer ("Get many rows1"),
# computed the next sequential claim_id ("Code in JavaScript1"), and
# written a new row - claim_id / policy_no / accident_date - into the
# Baserow "claims" table ("Create a row", database 561753, table
# 1206084). So instead of trusting caller-supplied identifiers, the
# agent's first real step asks the CRM itself which claim these just-
# uploaded documents belong to (the most recently created row) and pulls
# claim_id/policy_number/customer_id from there.
#
#   START -> receive_claim -> lookup_claim --(not found)--> decision
#                                  |(resolved from CRM)
#                                  v
#                             check_policy --(inactive)--> decision
#                                  |(active)
#                                  v
#                          analyze_documents -> update_accident_date -> decision -> END
#
# Nothing in this flow is mocked or hardcoded: lookup_claim, check_policy
# and update_accident_date all spin up a small ReAct agent
# (langgraph.prebuilt.create_react_agent) armed with Baserow's own hosted
# MCP server as its tools (see your Baserow account -> Settings -> MCP
# server), and ask THAT agent to go read or write the CRM itself - claims
# and policies are real Baserow tables, looked up live. lookup_claim is a
# read: it's the only source of
# claim_id/customer_id/policy_number in this whole flow - if it can't
# resolve a claim, the graph halts with CLAIM_NOT_FOUND rather than
# guessing. update_accident_date is a write: once analyze_documents has
# read the real accident date off the police report, it corrects the
# placeholder date n8n's "Create a row" node wrote at claim-creation time
# (best-effort - a failed write is logged but doesn't block the claim).
# analyze_documents is the one direct LLM call: it reads the text
# extracted from each uploaded PDF (via pypdf) and pulls out structured
# facts (accident date/type, repair estimate, garage name - garage name is
# captured for the record but there's no approved-vendor table in Baserow
# to verify it against). Photo PDFs typically have no extractable text at
# all - "photos_available" is decided deterministically from whether a
# file classified as photos was uploaded, not from the LLM reading an
# empty page. There's likewise no coverage-rules table mapping accident
# type to policy_type, so any claim against an active policy is treated as
# covered (check_policy already gated on the policy being active).
#
# CONFIG (add to the repo's root .env):
#   BASEROW_MCP_URL=<your Baserow account's MCP server URL, e.g.
#     https://api.baserow.io/mcp/<token>/sse - from Baserow ->
#     My settings -> MCP server -> Create endpoint. Treat it like a
#     password: it has full read/write access to your Baserow workspace.>
#
# RUN LOCALLY:
#   python 14_advanced/15_n8n/1_claim_analysis_agent.py
#   (serves http://localhost:8020 - see /docs for interactive Swagger UI)
#
# TRY IT (this folder already has the 3 sample PDFs n8n's Gmail workflow
# would extract; for this to resolve anything other than CLAIM_NOT_FOUND,
# a row must already exist in the Baserow "claims" table, e.g. by running
# the n8n workflow's CRM-write nodes first):
#   curl -X POST http://localhost:8020/analyze-claim -F "police_report=@14_advanced/15_n8n/Police_Report.pdf" -F "repair_estimate=@14_advanced/15_n8n/Repair_Estimate.pdf" -F "accident_photos=@14_advanced/15_n8n/Accident_Photos.pdf"
#
# WIRE INTO n8n:
#   Add an HTTP Request node after "Create a row" in 14_1_n8n_langgraph.json:
#   method POST, URL http://localhost:8020/analyze-claim, Body Content Type
#   "Form-Data" (multipart), with one binary field per attachment (reuse the
#   binary data already produced by the "Code in JavaScript" node - no OCR/
#   text-extraction node needed, this endpoint extracts PDF text itself). No
#   JSON fields required. The JSON this endpoint returns (status/reason/
#   estimated_amount/confidence) can then drive an n8n IF node - e.g. branch
#   to a human-review Slack/email alert when status is HUMAN_REVIEW, or
#   straight-through-process when AUTO_APPROVED.
# =====================================================================

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

AUTO_APPROVAL_LIMIT = 150_000       # claims at/under this are eligible for straight-through processing
MIN_DOCUMENTS = 3                   # police report + repair estimate + photographic evidence

# Baserow's hosted MCP server (see your account's Settings -> MCP server) -
# one URL per workspace, with the auth token embedded in the path itself.
# Treat it like a password: it grants read/write access to your whole
# Baserow workspace, so it lives only in .env (gitignored), never here.
BASEROW_MCP_URL = os.getenv("BASEROW_MCP_URL", "")
# IDs of the "insurance" database / "claims" table n8n writes into - see
# 14_1_n8n_langgraph.json's "Create a row" node. Given to the agent as
# hints; it still has to call the Baserow MCP tools itself to confirm.
BASEROW_DATABASE_ID = 561753
BASEROW_CLAIMS_TABLE_ID = 1206084

CRM_LOOKUP_PROMPT = """\
You have tools to read data from a Baserow workspace via MCP.

In database id {database_id} ("insurance"), find the table called "claims" \
(table id {table_id}). Its fields are: claim_id, policy_no, accident_date, \
amount. Find the single row with the highest/most recent claim_id - that is \
the claim these newly uploaded documents belong to.

Then, in the same database, find the table called "customers" (fields: \
customer_id, name, email, phone, policy_no, active). Find the row whose \
policy_no field equals that claim's policy_no, and use its customer_id \
field as customer_id.

When you are done, reply with exactly one line and nothing else, valid JSON \
and nothing before or after it:
RESULT: {{"found": true, "claim_id": "<claim_id>", "policy_number": "<policy_no>", "customer_id": "<customer_id>"}}
or, if the claims table has no rows at all:
RESULT: {{"found": false}}"""


CRM_CHECK_POLICY_PROMPT = """\
You have tools to read data from a Baserow workspace via MCP.

In database id {database_id} ("insurance"), find the table called \
"policies" (fields: policy_no, customer_id, vehicle, policy_type, expiry, \
active). Find the single row whose policy_no field equals "{policy_number}" \
exactly.

If you find it, read its active field (a boolean/checkbox - true means the \
policy is currently active, false means it is not), its policy_type, \
vehicle and expiry fields.

When you are done, reply with exactly one line and nothing else, valid JSON \
and nothing before or after it:
RESULT: {{"found": true, "active": true|false, "policy_type": "<policy_type>", "vehicle": "<vehicle>", "expiry": "<expiry>"}}
or, if no row with that policy number exists:
RESULT: {{"found": false}}"""


CRM_UPDATE_ACCIDENT_DATE_PROMPT = """\
You have tools to read and write data in a Baserow workspace via MCP.

In database id {database_id}, find the table called "claims" (table id \
{table_id}). Find the row whose claim_id field equals "{claim_id}" exactly, \
and update that row's accident_date field to "{accident_date}" - this \
overwrites whatever placeholder value is there now with the real accident \
date read from the police report.

When you are done, reply with exactly one line and nothing else, valid JSON \
and nothing before or after it:
RESULT: {{"updated": true}} - if you found the row and updated its accident_date
RESULT: {{"updated": false}} - if no row with that claim_id was found, or the update failed"""


async def run_baserow_mcp_agent(instruction: str, recursion_limit: int = 20) -> dict:
    """Shared helper: spin up a ReAct agent armed with Baserow's own hosted
    MCP tools, run one instruction, and parse its final `RESULT: {...}` line
    as JSON. Used for both reading (lookup_claim_in_crm) and writing
    (update_claim_accident_date) - Baserow's MCP server exposes both."""
    if not BASEROW_MCP_URL:
        return {"error": "BASEROW_MCP_URL is not configured"}

    client = MultiServerMCPClient({
        "baserow": {"transport": "sse", "url": BASEROW_MCP_URL},
    })
    tools = await client.get_tools()
    agent = create_react_agent(model=llm, tools=tools)

    result = await agent.ainvoke(
        {"messages": [{"role": "user", "content": instruction}]},
        config={"recursion_limit": recursion_limit},
    )
    final_text = result["messages"][-1].content

    match = re.search(r"RESULT:\s*(\{.*\})", final_text, re.DOTALL)
    if not match:
        return {"error": f"could not parse a RESULT line from the agent: {final_text!r}"}
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError:
        return {"error": f"agent returned malformed RESULT JSON: {final_text!r}"}


async def lookup_claim_in_crm() -> dict:
    """Ask the Baserow MCP agent which claim the just-uploaded documents
    belong to and resolve its claim_id/policy_number/customer_id - the
    caller supplies none of these, only the PDFs. Not mocked: this is a
    live read against the same "claims" table n8n's workflow writes to."""
    instruction = CRM_LOOKUP_PROMPT.format(
        database_id=BASEROW_DATABASE_ID,
        table_id=BASEROW_CLAIMS_TABLE_ID,
    )
    result = await run_baserow_mcp_agent(instruction, recursion_limit=20)
    result["found"] = bool(result.get("found"))
    return result


async def check_policy_in_crm(policy_number: str) -> dict:
    """Ask the Baserow MCP agent whether this policy number exists and is
    active - a live read against Baserow's "policies" table (policy_no,
    customer_id, vehicle, policy_type, expiry, active)."""
    instruction = CRM_CHECK_POLICY_PROMPT.format(
        database_id=BASEROW_DATABASE_ID,
        policy_number=policy_number,
    )
    result = await run_baserow_mcp_agent(instruction, recursion_limit=20)
    result["found"] = bool(result.get("found"))
    return result


async def update_claim_accident_date(claim_id: str, accident_date: str) -> dict:
    """Write the accident date read from the police report back into this
    claim's CRM row, correcting the placeholder date n8n's "Create a row"
    node writes at claim-creation time. A real Baserow write via MCP."""
    instruction = CRM_UPDATE_ACCIDENT_DATE_PROMPT.format(
        database_id=BASEROW_DATABASE_ID,
        table_id=BASEROW_CLAIMS_TABLE_ID,
        claim_id=claim_id,
        accident_date=accident_date,
    )
    result = await run_baserow_mcp_agent(instruction, recursion_limit=15)
    result["updated"] = bool(result.get("updated"))
    return result


# ---------------------------------------------------------------------
# Graph state - accumulates everything discovered as the claim moves
# through the graph, plus a running `log` of what each node did so the
# HTTP response can show the trace, not just the final verdict.
# ---------------------------------------------------------------------
class ClaimState(TypedDict):
    claim_id: str
    customer_id: str
    claim_type: str
    policy_number: str
    documents: List[Dict[str, str]]
    num_documents: int
    photos_uploaded: bool

    crm_verified: bool

    policy_status: str
    policy_coverage: str
    policy_expiry: str
    policy_active: bool

    accident_date: str
    vehicle: str
    accident_type: str
    estimated_repair_amount: float
    photos_available: bool
    documents_sufficient: bool
    document_confidence: float
    accident_date_synced: bool

    garage_name: str

    status: str
    reason: str
    confidence: float
    log: List[str]


class DocumentAnalysis(BaseModel):
    accident_date: str = Field(description="Date of the accident as stated in the documents, e.g. '15 Sept 2026'")
    vehicle: str = Field(description="Vehicle involved, e.g. 'Honda City'")
    accident_type: str = Field(description="e.g. Collision, Theft, Fire, Flood")
    estimated_repair_amount: float = Field(description="Estimated repair cost in INR as a plain number, e.g. 185000")
    garage_name: str = Field(description="Name of the garage/service centre doing the repair; empty string if not mentioned")
    photos_available: bool = Field(description="True if the documents mention accident photos/visual evidence being submitted")
    confidence: float = Field(ge=0.0, le=1.0, description="Your confidence in this extraction, 0 to 1")


doc_analysis_prompt = ChatPromptTemplate.from_template("""\
You are a claims document analyst. Read the documents below, submitted in \
support of a vehicle insurance claim, and extract the requested facts.

{documents_text}""")

doc_analysis_chain = doc_analysis_prompt | llm.with_structured_output(DocumentAnalysis)


# ---------------------------------------------------------------------
# Nodes
# ---------------------------------------------------------------------
def receive_claim(state: ClaimState) -> ClaimState:
    doc_types = ", ".join(doc.get("type", "document") for doc in state["documents"]) or "none"
    photos_uploaded = any(doc.get("type") == "photos" for doc in state["documents"])
    log = state["log"] + [
        f"[receive_claim] {len(state['documents'])} document(s) uploaded ({doc_types}) - "
        f"resolving claim identity from the CRM..."
    ]
    return {
        "num_documents": len(state["documents"]),
        "photos_uploaded": photos_uploaded,
        "status": "UNDER_INVESTIGATION",
        "log": log,
    }


async def lookup_claim_node(state: ClaimState) -> ClaimState:
    try:
        result = await lookup_claim_in_crm()
    except Exception as exc:
        result = {"found": False, "error": f"Baserow MCP call failed - {exc}"}

    found = bool(result.get("found"))
    if found:
        message = (
            f"[lookup_claim] resolved via Baserow MCP - claim {result.get('claim_id')} / "
            f"policy {result.get('policy_number')} / customer {result.get('customer_id')}"
        )
    else:
        message = f"[lookup_claim] could not resolve a claim from the CRM - {result.get('error', 'no matching row found')}"

    return {
        "crm_verified": found,
        "claim_id": result.get("claim_id") or state["claim_id"],
        "policy_number": result.get("policy_number") or state["policy_number"],
        "customer_id": result.get("customer_id") or state["customer_id"],
        "log": state["log"] + [message],
    }


def route_after_crm_lookup(state: ClaimState) -> str:
    return "check_policy" if state["crm_verified"] else "decision"


async def check_policy_node(state: ClaimState) -> ClaimState:
    try:
        result = await check_policy_in_crm(state["policy_number"])
    except Exception as exc:
        result = {"found": False, "error": f"Baserow MCP call failed - {exc}"}

    found = bool(result.get("found"))
    active = found and bool(result.get("active"))
    status = "Active" if active else ("Inactive" if found else "Not Found")
    log = state["log"] + [
        f"[check_policy] {state['policy_number']} -> {status} "
        f"(policy_type: {result.get('policy_type') or 'n/a'})"
    ]
    return {
        "policy_status": status,
        "policy_coverage": result.get("policy_type", ""),
        "policy_expiry": result.get("expiry", ""),
        "policy_active": active,
        "log": log,
    }


def route_after_policy(state: ClaimState) -> str:
    return "analyze" if state["policy_active"] else "decision"


async def analyze_documents_node(state: ClaimState) -> ClaimState:
    documents_text = "\n\n".join(
        f"[{doc.get('type', 'document')}]\n{doc.get('content', '')}" for doc in state["documents"]
    )
    result = await doc_analysis_chain.ainvoke({"documents_text": documents_text})

    # Photo PDFs are almost always image-only (no extractable text), so the
    # LLM reading empty/near-empty content can't be trusted alone here -
    # combine its read of the text with the deterministic fact that a file
    # classified as "photos" was actually uploaded.
    photos_available = state["photos_uploaded"] or result.photos_available
    sufficient = state["num_documents"] >= MIN_DOCUMENTS and photos_available

    log = state["log"] + [
        f"[analyze_documents] accident_type={result.accident_type}, "
        f"estimated_repair={result.estimated_repair_amount}, "
        f"photos_available={photos_available}, sufficient={sufficient}"
    ]
    return {
        "accident_date": result.accident_date,
        "vehicle": result.vehicle,
        "accident_type": result.accident_type,
        "estimated_repair_amount": result.estimated_repair_amount,
        "photos_available": photos_available,
        "document_confidence": result.confidence,
        "garage_name": result.garage_name,
        "documents_sufficient": sufficient,
        "log": log,
    }


async def update_accident_date_node(state: ClaimState) -> ClaimState:
    if not state["accident_date"]:
        return {"log": state["log"] + ["[update_accident_date] no accident_date extracted from documents - skipping CRM update"]}

    try:
        result = await update_claim_accident_date(state["claim_id"], state["accident_date"])
    except Exception as exc:
        result = {"updated": False, "error": f"Baserow MCP call failed - {exc}"}

    updated = bool(result.get("updated"))
    if updated:
        message = f"[update_accident_date] wrote accident_date='{state['accident_date']}' back to claim {state['claim_id']} in CRM"
    else:
        message = f"[update_accident_date] could not update CRM - {result.get('error', 'row not found or write rejected')}"

    return {"accident_date_synced": updated, "log": state["log"] + [message]}


def decision_node(state: ClaimState) -> ClaimState:
    if not state["crm_verified"]:
        who = f"claim {state['claim_id']}" if state["claim_id"] else "this submission"
        status, reason = "CLAIM_NOT_FOUND", f"Could not resolve a matching claim record in the CRM for {who} - cannot proceed"
    elif not state["policy_active"]:
        status, reason = "REJECTED", f"Policy {state['policy_number']} is not active"
    elif not state["documents_sufficient"]:
        status, reason = "PENDING_DOCUMENTS", "Insufficient documentation submitted (need police report, repair estimate and photographic evidence)"
    elif state["estimated_repair_amount"] > AUTO_APPROVAL_LIMIT:
        status, reason = "HUMAN_REVIEW", "Claim amount exceeds automatic processing limit"
    else:
        status, reason = "AUTO_APPROVED", "All checks passed and claim amount is within the automatic-processing limit"

    log = state["log"] + [f"[decision] {status} - {reason}"]
    return {"status": status, "reason": reason, "confidence": state["document_confidence"], "log": log}


# ---------------------------------------------------------------------
# Graph: START -> receive_claim -> lookup_claim -> (check_policy | decision)
#        check_policy -> (analyze_documents | decision)
#        analyze_documents -> update_accident_date -> decision -> END
# ---------------------------------------------------------------------
graph = StateGraph(ClaimState)
graph.add_node("receive_claim", receive_claim)
graph.add_node("lookup_claim", lookup_claim_node)
graph.add_node("check_policy", check_policy_node)
graph.add_node("analyze_documents", analyze_documents_node)
graph.add_node("update_accident_date", update_accident_date_node)
graph.add_node("decision", decision_node)

graph.add_edge(START, "receive_claim")
graph.add_edge("receive_claim", "lookup_claim")
graph.add_conditional_edges("lookup_claim", route_after_crm_lookup, {"check_policy": "check_policy", "decision": "decision"})
graph.add_conditional_edges("check_policy", route_after_policy, {"analyze": "analyze_documents", "decision": "decision"})
graph.add_edge("analyze_documents", "update_accident_date")
graph.add_edge("update_accident_date", "decision")
graph.add_edge("decision", END)

claim_graph = graph.compile()

# --------------------------
# Draw and save graph image (best-effort - needs internet access since
# draw_mermaid_png renders via the remote mermaid.ink API).
# --------------------------
try:
    import os
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    graph_path = os.path.join(BASE_DIR, "claim_analysis_graph.png")
    claim_graph.get_graph().draw_mermaid_png(output_file_path=graph_path)
    print(f"Graph image saved at: {graph_path}")
except Exception as exc:
    print(f"(skipped graph image - {exc})")


# ---------------------------------------------------------------------
# HTTP layer - this is what the n8n HTTP Request node calls. It takes raw
# PDFs as multipart/form-data (any field name(s) - n8n's binary property
# names vary run to run) and figures out claim_id/customer_id/policy_number
# itself via lookup_claim, so there is no JSON body to define at all.
# ---------------------------------------------------------------------
def extract_pdf_text(data: bytes) -> str:
    reader = PdfReader(BytesIO(data))
    return "\n".join(page.extract_text() or "" for page in reader.pages).strip()


def classify_document(filename: str) -> str:
    name = (filename or "").lower()
    if "police" in name:
        return "police_report"
    if "repair" in name or "estimate" in name:
        return "repair_estimate"
    if "photo" in name or "accident" in name:
        return "photos"
    return "other"


class ClaimResponse(BaseModel):
    claim_id: str
    status: str
    reason: str
    estimated_amount: float
    confidence: float
    details: dict


app = FastAPI(title="Claim Analysis Agent (LangGraph)")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/analyze-claim", response_model=ClaimResponse)
async def analyze_claim(request: Request) -> ClaimResponse:
    form = await request.form()
    uploads = [value for value in form.values() if isinstance(value, UploadFile)]
    if not uploads:
        raise HTTPException(status_code=400, detail="No PDF files were uploaded - send one or more PDFs as multipart/form-data")

    documents: List[Dict[str, str]] = []
    for upload in uploads:
        raw = await upload.read()
        doc_type = classify_document(upload.filename or "")
        text = extract_pdf_text(raw)
        if not text:
            text = f"({upload.filename or 'file'} has no extractable text - likely image-only content, e.g. photos)"
        documents.append({"type": doc_type, "content": text})

    initial_state: ClaimState = {
        "claim_id": "",
        "customer_id": "",
        "claim_type": "Vehicle accident",
        "policy_number": "",
        "documents": documents,
        "num_documents": 0,
        "photos_uploaded": False,
        "crm_verified": False,
        "policy_status": "",
        "policy_coverage": "",
        "policy_expiry": "",
        "policy_active": False,
        "accident_date": "",
        "vehicle": "",
        "accident_type": "",
        "estimated_repair_amount": 0.0,
        "photos_available": False,
        "documents_sufficient": False,
        "document_confidence": 0.0,
        "accident_date_synced": False,
        "garage_name": "",
        "status": "",
        "reason": "",
        "confidence": 0.0,
        "log": [],
    }

    result = await claim_graph.ainvoke(initial_state)

    for line in result["log"]:
        print(line)

    return ClaimResponse(
        claim_id=result["claim_id"],
        status=result["status"],
        reason=result["reason"],
        estimated_amount=result["estimated_repair_amount"],
        confidence=result["confidence"],
        details={
            "crm": {
                "verified": result["crm_verified"],
                "claim_id": result["claim_id"],
                "customer_id": result["customer_id"],
                "policy_number": result["policy_number"],
                "accident_date_synced": result["accident_date_synced"],
            },
            "policy": {
                "status": result["policy_status"],
                "policy_type": result["policy_coverage"],
                "expiry": result["policy_expiry"],
            },
            "documents": {
                "count": result["num_documents"],
                "types": [doc["type"] for doc in documents],
                "accident_date": result["accident_date"],
                "vehicle": result["vehicle"],
                "accident_type": result["accident_type"],
                "photos_available": result["photos_available"],
                "sufficient": result["documents_sufficient"],
            },
            "garage": {"name": result["garage_name"]} if result["garage_name"] else None,
            "log": result["log"],
        },
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8020)
