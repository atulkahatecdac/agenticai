"""backend.py - FastAPI service that puts the agent behind POST /ask.

Run (terminal 1, from this folder):
    uvicorn backend:app --reload --port 8000
Try it without the UI at http://127.0.0.1:8000/docs
"""
from fastapi import FastAPI
from pydantic import BaseModel

from agent import run_agent

app = FastAPI(title="Agentic AI App")


class AskRequest(BaseModel):
    query: str


@app.post("/ask")
def ask(req: AskRequest):
    answer = run_agent(req.query)
    return {"answer": answer}
