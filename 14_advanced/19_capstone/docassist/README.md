# DocAssist: an Agentic RAG app, deployed with Docker Compose

Upload PDFs, ask questions about them, and get answers from an **agent** that decides for itself when to search
the documents. The conversation is remembered in **Postgres**, and the whole app (frontend, backend and
database) runs as **three containers** that you deploy to a cloud VM with one command.

Slides: [`docassist.pptx`](docassist.pptx) (generated from [`deck_builder/`](deck_builder/)).

```
 Browser ──► frontend (Streamlit, port 8522) ──► backend (FastAPI) ──► db (Postgres + pgvector)
                                                     │                   ├─ chunks   : text + embeddings
                                                     └──► OpenAI API     └─ messages : conversation memory
```

| Part | What it teaches |
|---|---|
| RAG | PDF → chunks → embeddings → stored and searched in Postgres with **pgvector** |
| Agentic RAG | Search is a **tool**: the model decides whether to search, what to search for, and whether to search again |
| Short-term memory | Every message is saved in a Postgres table; the agent gets the **last 10 messages** of the session |
| Configuration | `OPENAI_API_KEY`, `POSTGRES_PASSWORD` and `DATABASE_URL` come from `.env`, never from the code or the image |
| Docker | One `Dockerfile` for the backend, one for the frontend, the official `pgvector/pgvector` image for the database |
| Docker Compose | Three services, a named volume, health checks, start order, only one public port |
| Cloud | An Ubuntu VM on AWS EC2 (or any cloud), reachable at `http://<public-ip>:8522` |

## The steps

Small scripts first (one idea each), then the real app built from the same pieces.

| Step | File | What it adds |
|---|---|---|
| 01 | `01a_embeddings.py` | Text → 1536 numbers; similar meaning = similar numbers (no database yet) |
| 02 | `02a_pgvector.py` | Store embeddings in Postgres and find the nearest one with `<=>` |
| 02 | `02b_ingest_pdfs.py` | Read the PDFs in `sample_docs/`, chunk, embed, store in a `chunks` table |
| 03 | `03a_rag.py` | Plain RAG: always search, then answer. Even "Hi" triggers a search |
| 04 | `04a_agentic_rag.py` | Agentic RAG: `search_documents` and `list_documents` are tools; the model decides |
| 05 | `05a_memory.py` | Short-term memory in a `messages` table: it survives a restart of the script |
| 06 | `backend/` | FastAPI: `/documents` (upload), `/chat`, `/history/{session_id}`, `/health` |
| 07 | `frontend/app.py` | Streamlit: upload PDFs, chat; it only talks to the backend |
| 08 | `docker-compose.yml` | The three containers together |
| 09 | (this README) | Deploy on a cloud VM |

The backend is steps 02–05 split into four files: `database.py` (all SQL), `rag.py` (PDF → chunks →
embeddings, search), `agent.py` (the tool loop + memory) and `main.py` (the endpoints).

## Setup (once)

From this folder, with the repo's `.venv` active (it already has everything in `requirements.txt`):

```bash
cp .env.example .env          # then put your OpenAI key in .env
docker run -d --name docassist-db -e POSTGRES_PASSWORD=docassist123 -e POSTGRES_DB=docassist -p 5433:5432 pgvector/pgvector:pg17
```

That container is the database for steps 02–07. It uses port **5433** so it doesn't clash with a Postgres
you may already have on 5432. Stop it with `docker stop docassist-db`, start it again with
`docker start docassist-db`.

## Steps 01–05: the scripts

```bash
python 01a_embeddings.py
python 02a_pgvector.py
python 02b_ingest_pdfs.py
python 03a_rag.py
python 04a_agentic_rag.py
python 05a_memory.py first
python 05a_memory.py second     # "And what about interns?" - only answerable with memory
```

What to look for in 04: `Hi, good morning!` gets **no** search, the Pune hotel question gets **one**, and the
public-holiday question usually gets **two** (one per policy), because the answer is spread across both PDFs.

## Steps 06–07: the app on your laptop

Two terminals, both with the `.venv` active:

```bash
cd backend
uvicorn main:app --port 8022 --reload           # API docs: http://localhost:8022/docs
```

```bash
cd frontend
streamlit run app.py --server.port 8522         # http://localhost:8522
```

Upload `sample_docs/leave_policy.pdf` from the sidebar and ask a question. The conversation id is in the URL
(`?sid=...`): refresh the page and the conversation is still there, because it comes from Postgres, not from
the browser.

## Step 08: Docker Compose

Stop the laptop backend and frontend first (Ctrl+C), then:

```bash
docker compose up -d --build
docker compose ps               # db, backend and frontend all "healthy" / "Up"
```

Open http://localhost:8522. This stack has its **own** database (an empty volume), so upload a PDF again.

| In `docker-compose.yml` | Why |
|---|---|
| `image: pgvector/pgvector:pg17` | Postgres with the vector extension already installed |
| `volumes: pgdata:` | The database files live in a named volume, so data survives `docker compose down` |
| `env_file: .env` | The API key reaches the backend at **run time**; it is never copied into an image (`.dockerignore`) |
| `DATABASE_URL: ...@db:5432/...` | Overrides the laptop address in `.env`; `db` is the service name, found by Docker's DNS |
| `depends_on: condition: service_healthy` | Backend starts only when Postgres is ready; frontend only when the backend is |
| Only the frontend has `ports:` | The database and the API are reachable only from inside the Compose network |

**The restart test** (the point of keeping memory in Postgres):

```bash
docker compose down             # removes all three containers (not the volume)
docker compose up -d
```

Refresh the browser: the documents and the conversation are still there. `docker compose down -v` also deletes
the volume, and with it all data.

Useful commands: `docker compose logs -f backend`, `docker compose exec db psql -U postgres -d docassist`
(then `SELECT session_id, role, left(content, 60) FROM messages;`).

## Step 09: deploy on a cloud VM (AWS EC2)

The same `docker compose` command on a VM. More detail on each step:
[`18_Dockerizing/4_streamlit_fastapi_fullstack`](../../18_Dockerizing/4_streamlit_fastapi_fullstack/README.md#run-it-on-aws-ec2).

**1. Launch an instance:** Ubuntu Server 24.04 LTS, `t3.small` (2 GB RAM), 20 GB disk, a key pair, and a
security group that allows **SSH (22)** and **Custom TCP 8522**, both from **My IP**. Do not open 5432 or
8000.

**2. Install Docker**

```bash
ssh -i my-key.pem ubuntu@<public-ip>
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker ubuntu && exit          # log in again for the group to apply
```

**3. Get the code, create `.env` on the server**

```bash
git clone https://github.com/atulkahatecdac/agenticai.git
cd agenticai/14_advanced/19_capstone/docassist
cp .env.example .env
nano .env                       # your OpenAI key + a strong POSTGRES_PASSWORD
chmod 600 .env
```

`.env` is git-ignored, so it never comes with `git clone`: you create it on each machine. Use letters and
digits in `POSTGRES_PASSWORD`, because it is also part of a URL.

**4. Start it:** `docker compose up -d --build`, then open `http://<public-ip>:8522`. All services have
`restart: unless-stopped`, so the app comes back after a VM reboot.

**5. Clean up:** `docker compose down`, then stop or terminate the instance.

Other clouds work the same way: an Azure VM (open the port in the Network Security Group) or a GCP Compute
Engine VM (a firewall rule).

## Troubleshooting

| Symptom | Cause |
|---|---|
| `connection refused` on port 5433 (steps 02–07) | The `docassist-db` container is not running: `docker start docassist-db` |
| `KeyError: 'DATABASE_URL'` | No `.env` in this folder: `cp .env.example .env` |
| Backend stays `unhealthy` | `docker compose logs backend`; usually a wrong password in `.env` |
| Changed `POSTGRES_PASSWORD`, now login fails | Postgres sets the password only when the volume is first created: `docker compose down -v` (deletes data) |
| Page does not open on the VM | Port 8522 not allowed in the security group, or you used `https://` instead of `http://` |
| `openai.APIConnectionError` | Check `OPENAI_BASE_URL` is not set in your shell to a proxy that isn't running |
| `AuthenticationError` | Wrong key in `.env`. The scripts use `load_dotenv(override=True)`, so `.env` beats the shell |

## Going further

- HTTPS: put Caddy or nginx in front of the frontend, with a domain name and a certificate.
- Secrets: AWS Secrets Manager or SSM Parameter Store instead of a `.env` file on the VM.
- Managed database: Amazon RDS for PostgreSQL (supports pgvector) instead of the `db` container.
- Better retrieval: an HNSW index on `chunks.embedding`, hybrid keyword + vector search, reranking.
- Users: log in, and store `user_id` with each session.
