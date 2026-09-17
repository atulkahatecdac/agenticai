import logging
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException

from app.queue import build_redis_client, enqueue_job, get_job
from app.schemas import AskRequest, IngestRequest, JobAccepted, JobStatusResponse

# =====================================================================
# A "full agent stack": FastAPI + ChromaDB + Redis + a separate worker
# process. The difference from ../1_fastapi_langchain and
# ../2_fastapi_langchain_mysql_history is architectural, not just "one more
# container": THIS api never calls an LLM or touches Chroma at all. Every
# endpoint below does nothing but push a job onto Redis (queue.py) and return
# immediately - all the actual RAG work (embedding, vector search, the LLM
# call) happens in app/worker.py, a completely separate container.
#
# WHY: an LLM call (or an embedding call over a large document) can take
# seconds - fine for a background job, bad for something blocking an HTTP
# request that a load balancer or browser might time out. Decoupling via a
# queue also means job-processing capacity scales independently of the API:
# see docker-compose.yml's note on `docker compose up -d --scale worker=3`.
#
# RUN:
#   cd 14_advanced/18_Dockerizing/3_fastapi_chromadb_redis_worker
#   cp .env.example .env   # then fill in OPENAI_API_KEY (only the worker uses it)
#   docker compose up -d --build
#
# TRY IT - see README.md for the full walkthrough, short version:
#   curl -X POST http://localhost:8000/documents \
#        -H "Content-Type: application/json" \
#        -d "{\"doc_id\": \"doc1\", \"text\": \"<some text>\"}"
#   curl http://localhost:8000/jobs/<job_id from above>
#   curl -X POST http://localhost:8000/ask \
#        -H "Content-Type: application/json" -d "{\"question\": \"...\"}"
#   curl http://localhost:8000/jobs/<job_id from above>
# =====================================================================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("agent_stack")


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_dotenv()
    app.state.redis = build_redis_client()
    logger.info("API ready - Redis client connected (no OpenAI/Chroma access from this process)")
    yield
    await app.state.redis.aclose()


app = FastAPI(title="Agent Stack: FastAPI + ChromaDB + Redis + Worker", lifespan=lifespan)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.post("/documents", response_model=JobAccepted, status_code=202)
async def ingest(payload: IngestRequest) -> JobAccepted:
    job_id = await enqueue_job(app.state.redis, "ingest", {"doc_id": payload.doc_id, "text": payload.text})
    return JobAccepted(job_id=job_id)


@app.post("/ask", response_model=JobAccepted, status_code=202)
async def ask(payload: AskRequest) -> JobAccepted:
    job_id = await enqueue_job(app.state.redis, "ask", {"question": payload.question})
    return JobAccepted(job_id=job_id)


@app.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def job_status(job_id: str) -> JobStatusResponse:
    job = await get_job(app.state.redis, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found (it may have expired or never existed)")
    return JobStatusResponse(job_id=job_id, status=job["status"], result=job["result"])
