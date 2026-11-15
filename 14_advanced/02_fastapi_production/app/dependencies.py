"""Dependencies: small functions FastAPI calls for you and passes into endpoints with Depends().

Endpoints never build their own LLM client - they declare what they need.
That makes the code shorter, and tests can swap any dependency (see test_api.py).
"""
from functools import lru_cache

from fastapi import Depends
from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI

from app.config import Settings, get_settings


@lru_cache
def _build_llm(model: str) -> BaseChatModel:
    # Built once per model name and reused - not once per request.
    return ChatOpenAI(model=model, temperature=0)


def get_llm(settings: Settings = Depends(get_settings)) -> BaseChatModel:
    return _build_llm(settings.model)

