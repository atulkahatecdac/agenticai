# ADR 0003 – SQLite checkpoints, so the API runs as a single instance

- **Status:** accepted for the capstone; revisit before scaling out
- **Date:** 2026-11

## Context
Tickets paused at the approval gate live in a LangGraph SQLite checkpoint (`data/checkpoints.db`).
The 19_11 load test shows ~1 s per ticket alone but a p50 of ~8 s with 10 concurrent customers: all
tickets share one Python process.

## Decision
Keep SQLite and one API instance for the capstone; mount `data/` as a volume so paused tickets survive a
container restart (`deploy/docker-compose.yml`).

## Consequences
- Simple to run and inspect.
- The API's ticket list is in memory, so after a restart the API rebuilds the paused tickets from the
  checkpoints (`_recover_waiting_tickets` in `19_7_api.py`). A container restart test found this gap: the
  checkpoint survived, but the API answered "Unknown ticket".
- To scale out (several replicas, or Cloud Run, whose disks are not shared), move checkpoints to a shared
  store – the Redis or Postgres checkpointer from Module 08 – and the in-memory ticket registry with them.
