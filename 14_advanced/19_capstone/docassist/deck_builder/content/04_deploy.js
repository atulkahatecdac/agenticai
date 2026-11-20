module.exports = {
  section: "Deployment",
  slides: [
    {
      title: "Environment Variables",
      subtitle: "Secrets and addresses come from the environment – never from the code or the image",
      demo: ".env.example  ·  docker-compose.yml",
      blocks: [
        { type: "table", size: 10.5, widths: [1.9, 1.5, 2.3, 2.3], head: ["Variable", "Read by", "On the laptop", "In Docker Compose"], rows: [
          ["OPENAI_API_KEY", "backend", ".env", ".env via `env_file:`"],
          ["POSTGRES_PASSWORD", "db", "`docker run -e ...`", ".env, as `${POSTGRES_PASSWORD}`"],
          ["DATABASE_URL", "backend", ".env → localhost:5433", "set in compose → `db:5432`"],
          ["BACKEND_URL", "frontend", "default localhost:8022", "set in compose → `backend:8000`"],
        ] },
        { type: "cols", cols: [
          [{ type: "bullets", size: 10.5, items: [
            "`.env` is git-ignored: create it on every machine",
            "`.dockerignore` keeps `.env` out of the images",
          ] }],
          [{ type: "bullets", size: 10.5, items: [
            "Each container gets only what it needs",
            "Production: a secrets manager instead of a file",
          ] }],
        ] },
      ],
    },
    {
      title: "08 – The Dockerfiles",
      subtitle: "One per service we write; the database uses the official image",
      demo: "backend/Dockerfile  ·  frontend/Dockerfile",
      split: [1.1, 1],
      left: [
        { type: "code", caption: "backend/Dockerfile", code:
"FROM python:3.12-slim\nWORKDIR /app\n\nCOPY requirements.txt .\nRUN pip install --no-cache-dir -r requirements.txt\n\nCOPY . .\n\nRUN useradd --create-home appuser\nUSER appuser\n\nEXPOSE 8000\nCMD [\"uvicorn\", \"main:app\", \"--host\", \"0.0.0.0\", \"--port\", \"8000\"]" },
      ],
      right: [
        { type: "icons", items: [
          { icon: "FaLayerGroup", title: "requirements.txt first", text: "A code change doesn't reinstall every package" },
          { icon: "FaUserShield", title: "USER appuser", text: "Not root inside the container" },
          { icon: "FaNetworkWired", title: "--host 0.0.0.0", text: "Accept connections from other containers" },
          { icon: "FaBan", title: ".dockerignore", text: "No .env, no __pycache__ in the image" },
        ] },
      ],
    },
    {
      title: "08 – docker-compose.yml",
      subtitle: "Three services, one volume, health checks – and a single public port",
      demo: "docker-compose.yml  →  docker compose up -d --build",
      split: [1.1, 1],
      left: [
        { type: "code", caption: "docker-compose.yml (shortened)", size: 8.5, code:
"services:\n  db:\n    image: pgvector/pgvector:pg17\n    environment:\n      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}\n      POSTGRES_DB: docassist\n    volumes: [pgdata:/var/lib/postgresql/data]\n    healthcheck: {test: pg_isready ...}\n  backend:\n    build: ./backend\n    env_file: .env\n    environment: {DATABASE_URL: postgresql://...@db:5432/docassist}\n    depends_on: {db: {condition: service_healthy}}\n  frontend:\n    build: ./frontend\n    environment: {BACKEND_URL: http://backend:8000}\n    ports: [\"8522:8501\"]\n    depends_on: {backend: {condition: service_healthy}}\nvolumes:\n  pgdata:" },
      ],
      right: [
        { type: "icons", size: 10.5, items: [
          { icon: "FaHardDrive", title: "Named volume pgdata", text: "Data survives `docker compose down`" },
          { icon: "FaSignature", title: "Service names are host names", text: "`db`, `backend` – Docker's DNS finds them" },
          { icon: "FaHeartPulse", title: "Start order by health", text: "db ready → backend → frontend" },
          { icon: "FaDoorOpen", title: "Only 8522 is published", text: "Database and API stay private" },
        ] },
      ],
    },
    {
      title: "The Restart Test",
      subtitle: "Why the memory lives in Postgres: remove every container and nothing is lost",
      demo: "docker compose down  ·  docker compose up -d",
      split: [1, 1],
      left: [
        { type: "code", caption: "terminal", code:
"docker compose up -d --build\ndocker compose ps          # all healthy\n\n# ask a question in the browser\n\ndocker compose down        # containers gone\ndocker compose up -d\n\n# refresh: documents and chat are still there\n\ndocker compose down -v     # -v also deletes the data" },
      ],
      right: [
        { type: "table", size: 10.5, widths: [2, 2.2], head: ["What", "Where it lives"], rows: [
          ["Uploaded documents", "chunks table → volume"],
          ["Conversation memory", "messages table → volume"],
          ["Session id", "the browser's URL"],
          ["Containers", "replaceable"],
        ] },
        { type: "callout", eyebrow: "Stateless app, stateful database", text: "Backend and frontend can be rebuilt, restarted or scaled at any time." },
      ],
    },
    {
      title: "09 – Deploy on a Cloud VM",
      subtitle: "The same compose command on an Ubuntu VM – AWS EC2 here, any cloud works",
      demo: "README.md  →  Step 09",
      split: [1, 1.15],
      left: [
        { type: "steps", size: 10.5, gap: 0.06, items: [
          { title: "Launch Ubuntu 24.04, t3.small", text: "Security group: SSH 22 and TCP 8522 from My IP" },
          { title: "Install Docker", text: "curl -fsSL https://get.docker.com | sudo sh" },
          { title: "Clone, create .env on the server", text: "Real key, strong password, chmod 600" },
          { title: "docker compose up -d --build", text: "Open http://<public-ip>:8522" },
        ] },
      ],
      right: [
        { type: "code", caption: "on the VM", code:
"git clone https://github.com/atulkahatecdac/agenticai.git\ncd agenticai/14_advanced/19_capstone/docassist\ncp .env.example .env\nnano .env\nchmod 600 .env\ndocker compose up -d --build" },
        { type: "bullets", size: 10.5, items: [
          "Do not open 5432 or 8000",
          "`restart: unless-stopped` brings it back after a reboot",
          "Done? `docker compose down`, stop the instance",
        ] },
      ],
    },
    {
      kind: "summary",
      title: "Summary",
      subtitle: "Build → test → containerize → deploy → a public URL",
      built: [
        { tag: "01–02", title: "RAG on Postgres", text: "Embeddings, pgvector, PDF ingestion" },
        { tag: "03–04", title: "Agentic RAG", text: "From always-search to a model that decides" },
        { tag: "05", title: "Memory", text: "Short-term, in a Postgres table" },
        { tag: "06–07", title: "The app", text: "FastAPI backend, Streamlit frontend" },
        { tag: "08–09", title: "Deployment", text: "Dockerfiles, Compose, a cloud VM" },
      ],
      takeaways: [
        "Agentic RAG: retrieval is a tool the model chooses",
        "One Postgres holds vectors and memory",
        "Configuration comes from the environment",
        "Containers are replaceable; the volume is not",
        "Expose only the port users need",
      ],
    },
  ],
};
