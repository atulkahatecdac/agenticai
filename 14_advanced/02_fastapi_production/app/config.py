"""Settings, read once from the environment (.env in the repo root)."""
import os
from functools import lru_cache

from dotenv import load_dotenv
from pydantic import BaseModel

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, "..", "..", ".env"), override=True)


class Settings(BaseModel):
    model: str = "gpt-4o-mini"
    # Clients send this in the X-API-Key header to use /documents.
    # Not the OpenAI key: it protects YOUR API from strangers.
    app_api_key: str = "dev-key-change-me"
    max_upload_mb: float = 2.0


@lru_cache  # one Settings object for the whole process
def get_settings() -> Settings:
    return Settings(
        model=os.getenv("APP_MODEL", "gpt-4o-mini"),
        app_api_key=os.getenv("APP_API_KEY", "dev-key-change-me"),
        max_upload_mb=float(os.getenv("APP_MAX_UPLOAD_MB", "2")),
    )
