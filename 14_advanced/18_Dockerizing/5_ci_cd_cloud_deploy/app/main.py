"""The service CI tests, builds and deploys: a small agent endpoint with ops endpoints.

    uvicorn app.main:app --port 8000
"""
import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from langchain_core.language_models import BaseChatModel
from pydantic import BaseModel, Field

from app.config import APP_VERSION, MODEL, secret

log = logging.getLogger("uvicorn.error")
_state = {"ready": False, "llm": None}


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: build expensive things once, then declare the service ready.
    key = secret("OPENAI_API_KEY")
    _state["llm"] = None
    if key:
        from langchain_openai import ChatOpenAI
        _state["llm"] = ChatOpenAI(model=MODEL, temperature=0, api_key=key, timeout=30)
    _state["ready"] = True
    log.info("version %s ready (LLM configured: %s)", APP_VERSION, bool(key))
    yield
    # Shutdown (SIGTERM from Docker, Cloud Run or ECS): stop taking new work.
    # Uvicorn finishes in-flight requests before this runs.
    _state["ready"] = False
    log.info("version %s shutting down cleanly", APP_VERSION)


app = FastAPI(title="Agent service", version=APP_VERSION, lifespan=lifespan)


def get_llm() -> BaseChatModel:
    if _state["llm"] is None:
        raise HTTPException(503, "No OPENAI_API_KEY configured")
    return _state["llm"]


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2000)


class AskResponse(BaseModel):
    answer: str
    version: str


@app.post("/ask", response_model=AskResponse)
async def ask(req: AskRequest, llm: BaseChatModel = Depends(get_llm)) -> AskResponse:
    reply = await llm.ainvoke(f"Answer in at most two sentences: {req.question}")
    return AskResponse(answer=reply.content, version=APP_VERSION)


# Liveness: is the process alive? (Docker HEALTHCHECK, ECS health check)
@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


# Readiness: should traffic be sent here? (load balancers, blue/green switch)
@app.get("/ready")
def ready() -> dict:
    if not _state["ready"]:
        raise HTTPException(503, "not ready")
    return {"status": "ready", "version": APP_VERSION}


@app.get("/version")
def version() -> dict:
    return {"version": APP_VERSION}
