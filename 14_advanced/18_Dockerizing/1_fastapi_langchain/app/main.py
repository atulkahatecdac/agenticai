import logging
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException

from app.chain import build_summarize_chain
from app.schemas import SummarizeRequest, SummarizeResponse

# =====================================================================
# A minimal, production-shaped FastAPI + LangChain service: one real LangChain
# chain (chain.py), wrapped by one HTTP endpoint, run under uvicorn inside a
# multi-stage Docker image (see ../Dockerfile). The point of this example is
# the DOCKERIZING, not the LangChain logic itself - the chain is deliberately
# a single prompt | llm | parser pipeline, no agents/tools/memory.
#
# Why build the chain in a `lifespan` startup hook instead of at import time
# or lazily on first request: constructing ChatOpenAI() this early means a
# missing/invalid OPENAI_API_KEY surfaces as a container that fails its
# startup/health check immediately - "fail fast" - rather than as a 500 on
# whatever request happens to arrive first in production.
#
# LOCAL RUN (no Docker):
#   cd 14_advanced/18_Dockerizing/1_fastapi_langchain
#   pip install -r requirements.txt
#   cp .env.example .env   # then fill in OPENAI_API_KEY
#   uvicorn app.main:app --reload
#
# DOCKER RUN (plain docker, no compose):
#   cd 14_advanced/18_Dockerizing/1_fastapi_langchain
#   cp .env.example .env   # then fill in OPENAI_API_KEY
#   docker build -t fastapi-langchain-demo .
#   docker run -d --name fastapi-langchain-demo -p 8000:8000 --env-file .env fastapi-langchain-demo
#
# TRY IT:
#   curl http://localhost:8000/health
#   curl -X POST http://localhost:8000/summarize \
#        -H "Content-Type: application/json" \
#        -d "{\"text\": \"<a few paragraphs of text>\"}"
# =====================================================================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("fastapi_langchain_app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_dotenv()
    app.state.summarize_chain = build_summarize_chain()
    logger.info("LangChain summarize chain initialized")
    yield


app = FastAPI(title="FastAPI + LangChain Summarizer", lifespan=lifespan)


@app.get("/health")
async def health() -> dict:
    # Deliberately no LLM call here - a health check should reflect "is the
    # process up", not "is OpenAI reachable right now". The container's
    # HEALTHCHECK in the Dockerfile hits this endpoint.
    return {"status": "ok"}


@app.post("/summarize", response_model=SummarizeResponse)
async def summarize(payload: SummarizeRequest) -> SummarizeResponse:
    try:
        summary = await app.state.summarize_chain.ainvoke({"text": payload.text})
    except Exception as exc:
        logger.exception("summarization failed")
        raise HTTPException(status_code=502, detail="Upstream LLM call failed") from exc
    return SummarizeResponse(summary=summary.strip())
