"""15_9 - a LangGraph agent behind a REST API, so n8n can call it (and it can call n8n).

    n8n workflow 15_9 --HTTP POST /agent/run--> this service (LangGraph)
                                                   | needs a ticket?
    n8n workflow 15_3 <--HTTP POST /webhook/service-request--+

n8n does the plumbing (triggers, credentials, Slack/Gmail/Sheets nodes); the graph does the
reasoning that is awkward to draw as boxes. Each side calls the other over plain HTTP.

Run from 14_advanced/15_n8n:
    python 15_9_langgraph_agent_service.py            # http://localhost:8015/docs
    python 15_9_langgraph_agent_service.py --test     # one call in-process, no server
"""
import os
import sys
from typing import Literal, TypedDict

import httpx
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

load_dotenv(override=True)
sys.stdout.reconfigure(encoding="utf-8")

# The 15_3 webhook. From this script (on your PC) n8n is at localhost:5678.
N8N_TICKET_WEBHOOK = os.getenv("N8N_TICKET_WEBHOOK", "http://localhost:5678/webhook/service-request")
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)


class AgentState(TypedDict, total=False):
    question: str
    name: str
    email: str
    route: str
    ticket_id: str
    answer: str


class Route(BaseModel):
    route: Literal["answer", "ticket"] = Field(
        description="'ticket' if something is broken or needs a technician; 'answer' for how-to and general questions"
    )


def triage(state: AgentState) -> AgentState:
    return {"route": llm.with_structured_output(Route).invoke(
        f"A customer of an internet provider writes: {state['question']}").route}


def create_ticket(state: AgentState) -> AgentState:
    """Calls n8n: the 15_3 workflow validates the request and stores it in MySQL."""
    payload = {"name": state["name"], "email": state["email"], "issue": state["question"]}
    try:
        r = httpx.post(N8N_TICKET_WEBHOOK, json=payload, timeout=15)
        r.raise_for_status()
        return {"ticket_id": r.json().get("ticket_id", "unknown")}
    except Exception as e:                       # n8n down or 15_3 not published - degrade, don't crash
        print(f"[create_ticket] n8n call failed: {e}")
        return {"ticket_id": "not-created"}


def answer(state: AgentState) -> AgentState:
    if state.get("ticket_id"):
        made = state["ticket_id"] != "not-created"
        extra = (f"Ticket {state['ticket_id']} was created; mention it and say a technician will be in touch."
                 if made else "A ticket could not be created right now; apologise and ask them to try again later.")
    else:
        extra = "No ticket is needed; answer the question in up to 3 short steps."
    reply = llm.invoke(f"Reply to this customer, {state['name']}, in under 70 words. {extra}\n\nMessage: {state['question']}")
    return {"answer": reply.content}


g = StateGraph(AgentState)
g.add_node("triage", triage)
g.add_node("create_ticket", create_ticket)
g.add_node("answer", answer)
g.add_edge(START, "triage")
g.add_conditional_edges("triage", lambda s: s["route"], {"ticket": "create_ticket", "answer": "answer"})
g.add_edge("create_ticket", "answer")
g.add_edge("answer", END)
graph = g.compile()

# ---------------------------------------------------------------------
# The REST API n8n calls
# ---------------------------------------------------------------------
app = FastAPI(title="15_9 LangGraph agent for n8n")


class RunRequest(BaseModel):
    question: str = Field(min_length=3)
    name: str = "Customer"
    email: str = ""


class RunResponse(BaseModel):
    route: str
    ticket_id: str | None = None
    answer: str


@app.post("/agent/run", response_model=RunResponse)
def run(req: RunRequest) -> RunResponse:
    out = graph.invoke(req.model_dump())
    return RunResponse(route=out["route"], ticket_id=out.get("ticket_id"), answer=out["answer"])


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


if __name__ == "__main__":
    if "--test" in sys.argv:
        from fastapi.testclient import TestClient
        client = TestClient(app)
        for q in ["How do I change my Wi-Fi password?", "My router has been dead since yesterday, no lights at all."]:
            r = client.post("/agent/run", json={"question": q, "name": "Asha", "email": "asha@example.com"})
            print(f"\nQ: {q}\n-> {r.status_code} {r.json()}")
    else:
        uvicorn.run(app, host="0.0.0.0", port=8015)   # 0.0.0.0 so the n8n container can reach it
