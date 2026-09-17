# Composing a Full Agent Stack: FastAPI, ChromaDB, Redis, and a Worker

A four-container agent architecture, wired together with a single `docker-compose.yml`. This is the third example in `18_Dockerizing/`:

- `1_fastapi_langchain` — one container, synchronous request → LLM call → response.
- `2_fastapi_langchain_mysql_history` — two containers, still synchronous, MySQL added for persistent history.
- `3_fastapi_chromadb_redis_worker` (this one) — **four** containers, and the request path is no longer synchronous at all.

## Why this one is architecturally different

In folders 1 and 2, the FastAPI process itself called the LLM and returned the result in the same HTTP request. That's fine for a fast, single call. It falls apart once a request might involve an embedding call *and* a vector search *and* an LLM call — several seconds of latency that a browser, a load balancer, or an API gateway may simply time out waiting for.

This example decouples the two concerns with a **job queue**:

- The **`api`** container never calls OpenAI or ChromaDB at all. Every endpoint does nothing but push a job onto Redis and return immediately with a `job_id`.
- The **`worker`** container — a separate process with no HTTP server — pulls jobs off that queue and does the real work: embedding text, querying ChromaDB, calling the LLM.
- The caller polls `GET /jobs/{job_id}` until the job is `done`.

The payoff: **job-processing capacity scales independently of the API**, with zero code changes:

```
docker compose up -d --scale worker=3
```

Three worker containers will pull from the same Redis queue and process jobs in parallel. Nothing about `api` changes. This was verified live while building this example — sending several `/ask` requests with `--scale worker=3` running showed jobs landing on all three worker containers (confirmed via `docker logs` on each), not just one.

## The four services

| Service | Image | Role |
|---|---|---|
| `api` | built from `Dockerfile` | FastAPI gateway. Only talks to Redis. |
| `worker` | same image, different `command:` | Pulls jobs from Redis, calls OpenAI + ChromaDB. The only service meant to be scaled. |
| `redis` | `redis:7-alpine` | Job queue **and** job-status store — a different role than folder 2's Redis-as-cache. |
| `chromadb` | `chromadb/chroma:latest` | Vector store, run as its own service (not embedded in-process) so multiple worker replicas share one index instead of each holding a private copy. |

`api` and `worker` are **the same built image** — see `Dockerfile`'s single `CMD` (defaults to the api role) and `docker-compose.yml`'s `command:` override for the worker. One image, two roles, instead of maintaining two near-identical Dockerfiles.

## Request flow

```
POST /documents {doc_id, text}
        │
        ▼
   api pushes an "ingest" job onto Redis, returns 202 {job_id}
        │
        ▼
   worker BRPOPs the job, embeds the text (OpenAI), upserts into ChromaDB,
   writes {"status": "done", "result": {...}} back to Redis under the job's key
        │
        ▼
GET /jobs/{job_id}  →  {"status": "done", "result": {"doc_id": "...", "chars_indexed": 182}}
```

`POST /ask {question}` follows the identical shape: enqueue → worker retrieves the top-k matching chunks from ChromaDB, builds a prompt, calls the LLM, writes back `{"answer": "...", "sources": ["doc1"]}`.

## Why Redis is a queue here, not a cache

Folder 2 used Redis to *skip* work (return an already-computed summary). Here, Redis's job is to *hand off* work between two processes that don't share memory:

- `queue.py`'s `enqueue_job()` writes the job's initial `"pending"` status **before** pushing the job itself — so a client polling immediately after the `202` response never sees a `404` from a race with the worker not having started yet.
- `dequeue_job()` uses `BRPOP` (blocking pop) instead of a polling loop — the worker sleeps efficiently server-side instead of spinning in a `while True: check-and-sleep` loop.
- Every job result is written with a TTL (1 hour) so completed job records don't accumulate in Redis forever.

## Why ChromaDB runs as its own container

`langchain_chroma.Chroma` can run fully embedded in-process (no server at all) — that's how most of this repo's other Chroma examples use it. That only works for a single process, though. The moment you have more than one worker replica (the whole point of this example), each embedded instance would hold its own private, out-of-sync copy of the vector index. Running Chroma as its own service means every worker replica reads and writes the same collection over HTTP.

## A real gotcha hit while building this, worth knowing about

**`BRPOP` and `redis-py`'s socket timeout.** The worker's Redis client needs `socket_timeout=None` explicitly (see `queue.py`'s `build_redis_client()`). Without it, `redis-py`'s client-side socket read can time out *before* the server's own blocking timeout on `BRPOP` elapses, raising a spurious `redis.exceptions.TimeoutError` on every single empty-queue poll instead of cleanly returning `None`. This is a well-known pitfall with any blocking Redis command (`BRPOP`/`BLPOP`/`BLMPOP`) — the client-side timeout must be `None` or larger than the command's own blocking timeout.

**The `chromadb/chroma` image has no `curl`, `wget`, or `python` on its `PATH`.** Its Docker healthcheck (in `docker-compose.yml`) uses bash's `/dev/tcp` pseudo-device to send a raw HTTP request instead — and it has to invoke `bash` explicitly (`["CMD", "bash", "-c", ...]`), not `CMD-SHELL`, because this image's `/bin/sh` is `dash`, which doesn't support the `/dev/tcp` extension at all. Both facts were confirmed by exec'ing into a running container and probing directly, not assumed.

**The worker inherits the Dockerfile's `HEALTHCHECK`, which assumes an HTTP server on `:8000` — but the worker role never listens on that port.** Left unaddressed, Docker would report the worker container as permanently "unhealthy" for a check that doesn't apply to it. `docker-compose.yml` disables it explicitly for the `worker` service (`healthcheck: disable: true`).

## Running it

```
cd 14_advanced/18_Dockerizing/3_fastapi_chromadb_redis_worker
cp .env.example .env   # fill in OPENAI_API_KEY - only the worker container uses it
docker compose up -d --build
```

Startup order is enforced by `depends_on` + healthchecks: `redis` and `chromadb` must both report healthy before `worker` starts; `api` only waits on `redis`.

### Try it

Ingest a document:

```
curl -X POST http://localhost:8000/documents \
     -H "Content-Type: application/json" \
     -d "{\"doc_id\": \"doc1\", \"text\": \"SecureLife Insurance covers pre-existing conditions after a 2 to 4 year waiting period.\"}"
```

This returns `{"job_id": "..."}` immediately. Poll it:

```
curl http://localhost:8000/jobs/<job_id>
```

Once `"status": "done"`, ask a question about what you just ingested:

```
curl -X POST http://localhost:8000/ask \
     -H "Content-Type: application/json" \
     -d "{\"question\": \"How long is the waiting period for pre-existing conditions?\"}"
```

Poll `GET /jobs/<job_id>` again — the result includes both the answer and which document(s) it came from:

```json
{"status": "done", "result": {"answer": "...", "sources": ["doc1"]}}
```

### Scale the workers

```
docker compose up -d --scale worker=3
```

Send a few more requests and check which container picked up each job:

```
docker logs <worker-container-name> | grep "Processing job"
```

### Inspect the queue/results directly

```
docker exec -it redis_container redis-cli LRANGE agent:jobs:queue 0 -1
docker exec -it redis_container redis-cli KEYS "agent:jobs:status:*"
```

### Stop everything

```
docker compose down       # keeps the chroma_data volume (ingested documents persist)
docker compose down -v    # also removes the volume - starts fresh next time
```

## Files

```
3_fastapi_chromadb_redis_worker/
  app/
    main.py      # FastAPI: POST /documents, POST /ask, GET /jobs/{id} - talks only to Redis
    worker.py    # BRPOP loop - the only place OpenAI/ChromaDB get called
    rag.py       # embedding, vector search, and the LLM answer chain
    queue.py     # Redis job-queue helpers, shared by main.py and worker.py
    schemas.py   # Pydantic request/response models
  Dockerfile     # one image, two roles (see command: overrides in docker-compose.yml)
  docker-compose.yml
  requirements.txt
  .env.example
  .dockerignore
```
