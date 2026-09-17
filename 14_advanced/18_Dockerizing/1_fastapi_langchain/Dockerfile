# syntax=docker/dockerfile:1

# ---- Stage 1: builder - install dependencies into an isolated venv ----
# Keeping this in its own stage means pip's build tools/cache never end up in
# the final image - only the installed packages get copied forward below.
FROM python:3.12-slim AS builder

WORKDIR /app

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copying only requirements.txt first (before the app code) means Docker's
# layer cache can skip the `pip install` step entirely on rebuilds where only
# app/*.py changed - one of the biggest build-time wins in a Python Dockerfile.
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ---- Stage 2: runtime - copy only the venv + app code, run as non-root ----
FROM python:3.12-slim AS runtime

# Never run a production container as root - if the app is ever compromised,
# a non-root user limits what an attacker can do with that shell.
RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid appuser --shell /bin/bash --create-home appuser

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY app ./app

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

USER appuser

EXPOSE 8000

# Hits the app's own /health route (see app/main.py) - deliberately does NOT
# call the LLM, so the container reports healthy/unhealthy based on whether
# the process is serving requests, not on OpenAI's availability.
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=2)" || exit 1

# No --reload (that's a dev-only flag that watches the filesystem and adds
# overhead). Single worker here for simplicity - for real multi-core scaling,
# put multiple replicas of this container behind a load balancer/orchestrator
# rather than adding uvicorn workers inside one container.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
