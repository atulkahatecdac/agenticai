# syntax=docker/dockerfile:1
# Same multi-stage pattern as 1_fastapi_langchain, plus what CI/CD needs:
# a version baked in at build time, a readiness endpoint, and a graceful stop.

# ---- Stage 1: install dependencies into a venv ----
FROM python:3.12-slim AS builder
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ---- Stage 2: runtime ----
FROM python:3.12-slim AS runtime
RUN useradd --uid 1000 --create-home appuser
WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY app ./app

# CI passes the git commit: docker build --build-arg APP_VERSION=$GITHUB_SHA
ARG APP_VERSION=dev
ENV PATH="/opt/venv/bin:$PATH" PYTHONUNBUFFERED=1 APP_VERSION=${APP_VERSION}

USER appuser
EXPOSE 8000

# Liveness only - /health never calls the LLM.
HEALTHCHECK --interval=15s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=2)" || exit 1

# Exec form, so uvicorn is PID 1 and receives SIGTERM directly; it then
# finishes in-flight requests for up to 20 s before exiting.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--timeout-graceful-shutdown", "20"]
