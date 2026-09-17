import asyncio
import logging

from dotenv import load_dotenv

from app.queue import build_redis_client, dequeue_job, set_job_result
from app.rag import answer_question, build_answer_chain, build_vectorstore, ingest_document

# =====================================================================
# The worker: a plain asyncio loop, NOT a web server - it has no HTTP
# endpoints and nothing calls it directly. It just BRPOPs jobs off the Redis
# queue that app/main.py's endpoints pushed onto, and is the ONLY part of this
# stack that talks to OpenAI or ChromaDB (see rag.py). Run standalone:
#
#   python -m app.worker
#
# This same file is what docker-compose.yml's `worker` service runs via
# `command: python -m app.worker` - same built image as `api`, different
# command. See ../Dockerfile and docker-compose.yml's comments on why.
# =====================================================================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("agent_stack")


async def handle_job(vectorstore, answer_chain, job: dict) -> dict:
    job_type = job["type"]
    if job_type == "ingest":
        return await ingest_document(vectorstore, job["doc_id"], job["text"])
    if job_type == "ask":
        return await answer_question(vectorstore, answer_chain, job["question"])
    raise ValueError(f"unknown job type: {job_type!r}")


async def main() -> None:
    load_dotenv()
    redis_client = build_redis_client()
    vectorstore = build_vectorstore()
    answer_chain = build_answer_chain()
    logger.info("Worker ready - waiting for jobs")

    while True:
        job = await dequeue_job(redis_client, timeout=5)
        if job is None:
            continue  # BRPOP just timed out with an empty queue - loop and block again
        job_id = job["job_id"]
        logger.info("Processing job %s (%s)", job_id, job["type"])
        try:
            result = await handle_job(vectorstore, answer_chain, job)
            await set_job_result(redis_client, job_id, "done", result)
            logger.info("Job %s done", job_id)
        except Exception:
            logger.exception("Job %s failed", job_id)
            await set_job_result(redis_client, job_id, "error", "job failed - see worker logs")


if __name__ == "__main__":
    asyncio.run(main())
