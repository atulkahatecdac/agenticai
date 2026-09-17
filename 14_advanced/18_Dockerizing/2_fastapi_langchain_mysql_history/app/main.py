import logging
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query

from app.chain import build_summarize_chain
from app.db import create_pool, fetch_recent, save_summary
from app.schemas import HistoryItem, SummarizeRequest, SummarizeResponse

# =====================================================================
# Same FastAPI + LangChain summarizer as ../1_fastapi_langchain, but the
# second container is now MySQL instead of Redis - a persistent HISTORY log
# (every request's input text + summary + timestamp) rather than a cache.
# That's a real shift in purpose, not just a different database: nothing here
# is looked up before calling the LLM, every request still hits OpenAI, and
# the database write is a side effect afterward, not a shortcut around it.
#
# The docker-compose lesson from the Redis version still applies, actually
# more so here: MySQL takes noticeably longer than Redis to become ready on
# first boot (it runs its own init-db process before accepting connections),
# which is exactly why docker-compose.yml's `depends_on: condition:
# service_healthy` + a real healthcheck matter - without it, `api` would
# likely win the race and crash on its first connection attempt.
#
# Row writes degrade gracefully, same as the Redis cache did: see db.py's
# save_summary() - a MySQL outage logs a warning, it doesn't turn into a 502
# for the caller. Losing a history record is not the same severity as losing
# the summary the user actually asked for.
#
# RUN:
#   cd 14_advanced/18_Dockerizing/2_fastapi_langchain_mysql_history
#   cp .env.example .env   # then fill in OPENAI_API_KEY
#   docker compose up -d --build
#
# TRY IT:
#   curl -X POST http://localhost:8000/summarize \
#        -H "Content-Type: application/json" \
#        -d "{\"text\": \"<a few paragraphs of text>\"}"
#   curl http://localhost:8000/history
# =====================================================================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("fastapi_langchain_app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_dotenv()
    app.state.summarize_chain = build_summarize_chain()
    app.state.db_pool = await create_pool()
    logger.info("LangChain chain initialized; MySQL pool ready")
    yield
    app.state.db_pool.close()
    await app.state.db_pool.wait_closed()


app = FastAPI(title="FastAPI + LangChain Summarizer (with MySQL history)", lifespan=lifespan)


@app.get("/health")
async def health() -> dict:
    # Process liveness only, same as every other example in this directory -
    # deliberately doesn't touch MySQL or OpenAI. The container's HEALTHCHECK
    # hits this; docker-compose's own `mysql` healthcheck is what actually
    # verifies the database is ready (see docker-compose.yml).
    return {"status": "ok"}


@app.post("/summarize", response_model=SummarizeResponse)
async def summarize(payload: SummarizeRequest) -> SummarizeResponse:
    try:
        summary = await app.state.summarize_chain.ainvoke({"text": payload.text})
    except Exception as exc:
        logger.exception("summarization failed")
        raise HTTPException(status_code=502, detail="Upstream LLM call failed") from exc

    summary = summary.strip()
    await save_summary(app.state.db_pool, payload.text, summary)
    return SummarizeResponse(summary=summary)


@app.get("/history", response_model=list[HistoryItem])
async def history(limit: int = Query(10, ge=1, le=100)) -> list[HistoryItem]:
    rows = await fetch_recent(app.state.db_pool, limit)
    return [HistoryItem(**row) for row in rows]
