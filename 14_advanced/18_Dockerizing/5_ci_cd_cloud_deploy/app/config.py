"""Configuration from the environment - and secrets from files when they exist.

Docker secrets, Kubernetes secrets and Cloud Run's Secret Manager mounts all
put a secret in a FILE (e.g. /run/secrets/openai_api_key) instead of an
environment variable, so it never shows up in `docker inspect` or a crash
dump of the environment. The convention: NAME_FILE points to that file.
"""
import os


def secret(name: str) -> str | None:
    path = os.getenv(f"{name}_FILE")
    if path and os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return f.read().strip()
    return os.getenv(name)


APP_VERSION = os.getenv("APP_VERSION", "dev")       # set by CI to the git SHA - see the workflow
MODEL = os.getenv("APP_MODEL", "gpt-4o-mini")
