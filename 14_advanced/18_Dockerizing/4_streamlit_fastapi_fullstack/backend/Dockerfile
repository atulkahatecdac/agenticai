# syntax=docker/dockerfile:1
# Same multi-stage, non-root pattern as ../../1_fastapi_langchain/Dockerfile.

# ---- Stage 1: builder - install dependencies into an isolated venv ----
FROM python:3.12-slim AS builder
WORKDIR /app
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ---- Stage 2: runtime - only the venv + app code, as a non-root user ----
FROM python:3.12-slim AS runtime
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

# compose waits for this to pass before starting the frontend (depends_on:
# condition: service_healthy). /health never calls the LLM.
HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=5 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=2)" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
