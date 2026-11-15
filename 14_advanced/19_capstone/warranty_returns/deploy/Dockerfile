# syntax=docker/dockerfile:1
# One image for the whole capstone; docker-compose.yml runs it twice - as the
# API and as the Streamlit UI - with a different command.
# Build from the warranty_returns folder:  docker build -f deploy/Dockerfile -t capstone .

FROM python:3.12-slim AS builder
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY deploy/requirements-capstone.txt .
RUN pip install --no-cache-dir -r requirements-capstone.txt \
 && python -m spacy download en_core_web_lg          # Presidio's NLP model (~600 MB)

FROM python:3.12-slim AS runtime
RUN useradd --uid 1000 --create-home appuser
WORKDIR /app
RUN chown appuser:appuser /app          # the scripts write data/ next to themselves
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" PYTHONUNBUFFERED=1 CAPSTONE_NO_PUSH=1
COPY --chown=appuser:appuser *.py ./
USER appuser
# Bake the synthetic data and the policy index into the image (steps 1-2), so a
# fresh container is ready at once. Real systems load data from managed storage.
RUN python 19_1_generate_sample_data.py && python 19_2_ingest_policies.py > /dev/null
EXPOSE 8019 8501
HEALTHCHECK --interval=20s --timeout=5s --start-period=60s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8019/health', timeout=3)" || exit 1
CMD ["python", "19_7_api.py"]
