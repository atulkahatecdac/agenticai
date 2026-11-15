"""Production-style FastAPI layout: main.py only wires routers together.

Run from 14_advanced/02_fastapi_production:
    uvicorn app.main:app --reload        -> http://localhost:8000/docs
"""
from fastapi import Depends, FastAPI

from app.dependencies import require_api_key
from app.routers import chat, documents

app = FastAPI(title="Agent API", version="1.0.0")

app.include_router(chat.router)                                                 # open
app.include_router(documents.router, dependencies=[Depends(require_api_key)])   # every route needs X-API-Key


@app.get("/health", tags=["ops"])
def health() -> dict:
    return {"status": "ok"}
