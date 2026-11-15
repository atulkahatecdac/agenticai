"""Dependencies: small functions FastAPI calls for you and passes into endpoints with Depends().

Endpoints never build their own LLM client or check keys themselves - they declare what they need.
That makes the code shorter, and tests can swap any dependency (see test_api.py).
"""
from functools import lru_cache

from fastapi import Depends, Header, HTTPException, status
from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI

from app.config import Settings, get_settings


@lru_cache
def _build_llm(model: str) -> BaseChatModel:
    # Built once per model name and reused - not once per request.
    return ChatOpenAI(model=model, temperature=0)


def get_llm(settings: Settings = Depends(get_settings)) -> BaseChatModel:
    return _build_llm(settings.model)


def require_api_key(
    x_api_key: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> None:
    """Reject the request with 401 unless the X-API-Key header is right."""
    if x_api_key != settings.app_api_key:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing or wrong X-API-Key header")
