# syntax=docker/dockerfile:1

# ---- Stage 1: builder - install dependencies into an isolated venv ----
FROM python:3.12-slim AS builder

WORKDIR /app

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ---- Stage 2: runtime - copy only the venv + app code, run as non-root ----
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

# Only meaningful for the api role - the worker has no HTTP port, so
# docker-compose.yml doesn't apply a HEALTHCHECK to that service at all
# (there's nothing for one to check without adding an HTTP server the worker
# doesn't otherwise need).
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=2)" || exit 1

# Default command runs the api role; docker-compose.yml's `worker` service
# overrides this with `command: python -m app.worker` - same image, two roles.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
