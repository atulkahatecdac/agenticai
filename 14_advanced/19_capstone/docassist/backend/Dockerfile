FROM python:3.12-slim

WORKDIR /app

# Dependencies first: Docker caches this layer, so changing only the code
# does not reinstall every package on the next build
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Run as a normal user, not root
RUN useradd --create-home appuser
USER appuser

EXPOSE 8000
# 0.0.0.0 = accept connections from other containers, not only from inside this one
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
