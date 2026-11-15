# 5_ci_cd_cloud_deploy – from `git push` to a running cloud service

Examples 1–4 build and run containers by hand. This one adds what a team needs to ship safely:
automated tests, a CI/CD pipeline, a private registry, secrets that never touch the image, managed
deployment on **Google Cloud Run** or **AWS ECS (Fargate)**, and zero-downtime releases.

| Path | What it shows |
|---|---|
| `app/main.py` | The service: `POST /ask`, plus `/health` (liveness), `/ready` (readiness), `/version`; graceful shutdown |
| `app/config.py` | `secret("OPENAI_API_KEY")` reads `OPENAI_API_KEY_FILE` first – the Docker/Kubernetes/Cloud Run secrets convention |
| `tests/test_app.py` | 5 pytest tests with a fake LLM – CI runs them on every push, no key needed |
| `Dockerfile` | Multi-stage, non-root, `APP_VERSION` build arg (the git SHA), `HEALTHCHECK`, 20 s graceful shutdown |
| `docker-compose.yml` | Local run with a **Docker secret** (`secrets/openai_api_key.txt` mounted at `/run/secrets/…`) |
| `.github/workflows/ci-cd.yml` | test → build → push → **canary** on Cloud Run (10 %) → human approval → 100 %; or rolling deploy to ECS |
| `deploy/cloud_run_deploy.sh` | The same Cloud Run deployment by hand with `gcloud` (Artifact Registry, Secret Manager, autoscaling) |
| `deploy/ecs-task-definition.json`, `deploy/ecs_deploy.sh` | Fargate task definition (secrets from Secrets Manager, health check, CloudWatch logs) and a manual rollout |
| `blue_green/` | Blue/green on your laptop: two versions behind nginx, `switch.ps1`/`switch.sh` flips traffic with no dropped requests |

## Run it locally

```powershell
cd 14_advanced/18_Dockerizing/5_ci_cd_cloud_deploy
pytest -q tests                                   # 5 passed
Set-Content secrets/openai_api_key.txt "sk-..." -NoNewline
docker compose up -d --build                      # http://localhost:8018/docs
docker compose exec agent env | Select-String OPENAI   # only OPENAI_API_KEY_FILE - the key itself is not in the environment
docker compose down
```

## Blue/green without downtime

```powershell
cd blue_green
docker compose up -d --build                      # builds blue-1.0 and green-2.0
curl.exe localhost:8028/version                   # {"version":"blue-1.0"}
.\switch.ps1 green                                # checks green's /ready, then reloads nginx
curl.exe localhost:8028/version                   # {"version":"green-2.0"}
.\switch.ps1 blue                                 # rollback is the same command
docker compose down
```

Tested while a loop sent 300 requests through the proxy during the switch: 300 succeeded, 0 failed
(44 answered by blue, 256 by green).

## The pipeline

GitHub only runs workflows from `.github/workflows/` at the **root** of a repository, so this one does not
run on the course repo. To try it, push this folder as its own repository (then set `WORKDIR: .`), or copy
the workflow file into your repository's root `.github/workflows/`.

```
push to main ─► test (pytest + image smoke test)
                 ├─► DEPLOY_TARGET=gcp: build ─► Artifact Registry ─► Cloud Run revision with 0 % traffic
                 │                      ─► smoke-test its tagged URL ─► 10 % canary
                 │                      ─► "production" environment approval ─► 100 %
                 └─► DEPLOY_TARGET=aws: build ─► ECR ─► new task definition ─► ECS rolling update
pull request ──► test only
```

Neither cloud key is stored in GitHub: the jobs request a short-lived OIDC token, which GCP Workload
Identity Federation or an AWS IAM role trusts. One-time setup is in the comments at the top of the workflow.

## What was verified

- `pytest`: 5 passed. Docker image built; `docker compose up` served `/ready` and reported `healthy`;
  the key was mounted as a file and absent from the container environment.
- Blue/green: switch and rollback with both scripts, 0 failed requests out of 300.
- The workflow and compose files parse; the task definition is valid JSON.
- **Not run:** the cloud deploys (Cloud Run, ECS) and the GitHub Actions workflow itself – they need your
  own cloud account and repository settings. The commands are the documented `gcloud`/`aws` ones.
