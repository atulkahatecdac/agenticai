# 4 — Full-stack app: Streamlit frontend + FastAPI backend

The `02_frontend_backend_agent` app, split into **two containers** run by Docker Compose:

```
browser ──8501──▶ frontend (Streamlit) ──http://backend:8000──▶ backend (FastAPI) ──▶ OpenAI
```

| Path | What it is |
|---|---|
| `backend/` | FastAPI: `GET /health`, `POST /ask {"query": ...}` → `{"answer": ...}`; own Dockerfile and requirements |
| `frontend/` | Streamlit UI; reads `BACKEND_URL` from the environment; own Dockerfile and requirements |
| `docker-compose.yml` | Wires them together; publishes only port 8501 |
| `.env.example` | `OPENAI_API_KEY` – given to the backend only |

Three things this example teaches:

1. **Service names are host names.** Inside the frontend container `localhost` is the frontend itself,
   so compose sets `BACKEND_URL=http://backend:8000` – `backend` is the service name, resolved by Docker's DNS.
2. **Publish only what users need.** Port 8501 is published; the API has no `ports:` and is reachable
   only inside the compose network. The OpenAI key lives only in the backend container.
3. **Start in the right order.** `depends_on: condition: service_healthy` starts the UI only after the
   backend's `/health` check passes.

## Run it locally

```powershell
cd 14_advanced/18_Dockerizing/4_streamlit_fastapi_fullstack
copy .env.example .env          # then put your real OPENAI_API_KEY in .env
docker compose up -d --build
docker compose ps               # both services should become "healthy"
```

Open http://localhost:8501 and ask a question. `docker compose logs -f backend` shows the requests;
`docker compose down` stops everything. To try the API's `/docs` from your browser, uncomment the
`ports:` lines on the backend service.

## Run it on AWS (EC2)

The simplest path: one EC2 virtual machine running the same `docker compose` command.

**1. Launch an instance** (EC2 console → **Launch instance**)

| Setting | Value |
|---|---|
| AMI | Ubuntu Server 24.04 LTS |
| Instance type | `t3.small` (2 GB RAM is enough for both containers) |
| Key pair | Create one, download the `.pem` file |
| Security group | SSH (22) from **My IP**; Custom TCP **8501** from **My IP** |
| Storage | 20 GB gp3 |

Do not open port 8000 – the backend stays private, exactly as on your laptop.

**2. Connect and install Docker**

```bash
ssh -i my-key.pem ubuntu@<public-ip>

curl -fsSL https://get.docker.com | sudo sh     # Docker Engine + buildx + compose plugin
sudo usermod -aG docker ubuntu                  # run docker without sudo
exit                                            # log out and back in for the group to apply
ssh -i my-key.pem ubuntu@<public-ip>
docker compose version
```

**3. Get the code and the key**

```bash
git clone https://github.com/atulkahatecdac/agenticai.git
cd agenticai/14_advanced/18_Dockerizing/4_streamlit_fastapi_fullstack
cp .env.example .env
nano .env               # paste your OPENAI_API_KEY
chmod 600 .env
```

**4. Start it**

```bash
docker compose up -d --build
docker compose ps
```

Open `http://<public-ip>:8501`. Because both services use `restart: unless-stopped` and Docker starts
on boot, the app comes back by itself after an instance reboot.

**5. Clean up** – `docker compose down`, then **stop** (keeps the disk) or **terminate** the instance
so it stops costing money.

### From demo to production on AWS

| Concern | Demo above | Production |
|---|---|---|
| Secrets | `.env` file on the VM | AWS Secrets Manager or SSM Parameter Store, injected at start |
| Images | built on the VM | built in CI, pushed to **Amazon ECR** |
| Running | one VM, `docker compose` | **ECS on Fargate** (one service per container) or App Runner |
| HTTPS | plain HTTP on 8501 | Application Load Balancer + certificate from ACM, port 443 only |
| Address | public IP changes on stop/start | Elastic IP or a domain in Route 53 |
| Updates | `git pull && docker compose up -d --build` | Blue/green or canary releases (next slides) |
