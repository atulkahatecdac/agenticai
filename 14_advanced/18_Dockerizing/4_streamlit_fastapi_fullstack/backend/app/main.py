import logging
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.agent import build_llm, run_agent

# =====================================================================
# Backend of a full-stack app: Streamlit (../frontend) -> this FastAPI
# service -> an LLM. The app is the 02_frontend_backend_agent demo; the
# point here is running the two halves as two containers with compose.
#
# The frontend reaches this service at http://backend:8000 - "backend" is
# the compose SERVICE NAME, resolved by Docker's internal DNS. This port is
# not published to the host at all: only the UI is meant to be reachable.
#
# LOCAL RUN (no Docker), from this backend/ folder:
#   pip install -r requirements.txt
#   uvicorn app.main:app --reload       # needs OPENAI_API_KEY in ../.env or the shell
# =====================================================================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("fullstack_backend")


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_dotenv()
    # Built at startup, not per request: a missing OPENAI_API_KEY makes the
    # container fail immediately ("fail fast") instead of on the first question.
    app.state.llm = build_llm()
    logger.info("LLM client initialized")
    yield


app = FastAPI(title="Full-Stack Agent API", lifespan=lifespan)


class AskRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=4000)


class AskResponse(BaseModel):
    answer: str


@app.get("/health")
def health():
    # Deliberately does NOT call the LLM: compose uses this to decide when the
    # frontend may start, and that should not depend on OpenAI being up.
    return {"status": "ok"}


@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest):
    try:
        return AskResponse(answer=run_agent(app.state.llm, req.query))
    except Exception as e:  # surface LLM/API failures as a clean 502, not a stack trace
        logger.exception("LLM call failed")
        raise HTTPException(status_code=502, detail=f"LLM call failed: {e}") from e
