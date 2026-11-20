# 14d: the 13a web app in a container.
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# The web app plus the two MCP servers it starts, and the files they read.
COPY 13a_api_agent.py 12a_mcp_server_sqlite.py 11a_policy_server.py ./
COPY policies/ policies/
COPY static/ static/

EXPOSE 8000
CMD ["uvicorn", "13a_api_agent:app", "--host", "0.0.0.0", "--port", "8000"]
