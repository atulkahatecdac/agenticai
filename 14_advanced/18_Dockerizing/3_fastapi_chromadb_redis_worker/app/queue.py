import json
import os
import uuid
from typing import Any, Optional

import redis.asyncio as redis

# This is Redis used as a JOB QUEUE + job-status store - a different role than
# ../2_fastapi_langchain_mysql_history's earlier use as a cache. Same client
# library, genuinely different architectural purpose: here it's the thing that
# decouples the api container from the worker container entirely.
REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")
QUEUE_KEY = "agent:jobs:queue"
JOB_KEY_PREFIX = "agent:jobs:status:"
JOB_TTL_SECONDS = 3600


def build_redis_client() -> redis.Redis:
    # socket_timeout=None is required for BRPOP to actually block: without it,
    # redis-py's client-side socket read can time out BEFORE the server's
    # blocking timeout elapses, raising a spurious redis.exceptions.TimeoutError
    # on every empty-queue poll instead of cleanly returning None.
    return redis.Redis.from_url(REDIS_URL, decode_responses=True, socket_timeout=None)


async def enqueue_job(client: redis.Redis, job_type: str, payload: dict) -> str:
    job_id = uuid.uuid4().hex
    job = {"job_id": job_id, "type": job_type, **payload}
    # Write the "pending" status BEFORE pushing the job, so a client polling
    # /jobs/{id} immediately after the 202 response never sees a 404 due to a
    # race with the worker not having started yet.
    await client.set(JOB_KEY_PREFIX + job_id, json.dumps({"status": "pending", "result": None}), ex=JOB_TTL_SECONDS)
    await client.lpush(QUEUE_KEY, json.dumps(job))
    return job_id


async def dequeue_job(client: redis.Redis, timeout: int = 5) -> Optional[dict]:
    # BRPOP blocks server-side for up to `timeout` seconds instead of the
    # worker busy-polling in a tight loop - it sleeps efficiently when the
    # queue is empty and wakes up the instant a job is pushed.
    item = await client.brpop(QUEUE_KEY, timeout=timeout)
    if item is None:
        return None
    _, raw_job = item
    return json.loads(raw_job)


async def set_job_result(client: redis.Redis, job_id: str, status: str, result: Any) -> None:
    await client.set(JOB_KEY_PREFIX + job_id, json.dumps({"status": status, "result": result}), ex=JOB_TTL_SECONDS)


async def get_job(client: redis.Redis, job_id: str) -> Optional[dict]:
    raw = await client.get(JOB_KEY_PREFIX + job_id)
    if raw is None:
        return None
    return json.loads(raw)
