const M = "18_Dockerizing/";
const FS = M + "4_streamlit_fastapi_fullstack/";

module.exports = {
  section: "Module 18 – Dockerizing and Deploying",
  slides: [
    {
      kind: "opener",
      eyebrow: "Module 18",
      title: "Dockerizing and Deploying AI Agents",
      subtitle: "Package an agent as an image, run whole stacks with Compose, and release new versions safely",
      goals: [
        { icon: "FaDocker", title: "Understand images and containers", text: "layers and the build cache" },
        { icon: "FaFileCode", title: "Write a good Dockerfile", text: "multi-stage, non-root, with a health check" },
        { icon: "FaLayerGroup", title: "Compose multi-container stacks", text: "API + MySQL; a queue; a Streamlit + FastAPI full stack" },
        { icon: "FaAws", title: "Run it on AWS", text: "the same compose stack on an EC2 instance" },
        { icon: "FaCodeBranch", title: "Release without downtime", text: "blue/green and canary deployments" },
      ],
      agenda: [
        "Docker key terms",
        "A FastAPI + LangChain image",
        "Multi-stage builds",
        "Docker Compose: API + MySQL",
        "A full agent stack with a worker queue",
        "A full-stack app: Streamlit + FastAPI",
        "Running it on AWS (EC2)",
        "Blue/green deployment",
        "Canary deployment",
      ],
    },
    {
      title: "Docker: Key Terms",
      subtitle: "Software for building portable images and running them as containers",
      demo: "Concept",
      blocks: [
        { type: "tiles", cols: 4, items: [
          { icon: "FaBoxOpen", title: "Image", text: "The blueprint or package containers are made from" },
          { icon: "FaCube", title: "Container", text: "A running instance of an image" },
          { icon: "FaLayerGroup", title: "Layer", text: "One filesystem change inside an image" },
          { icon: "FaBolt", title: "Build cache", text: "Reuses unchanged layers to speed up builds" },
        ] },
      ],
    },
    { kind: "image", src: "docker_image_layers.png", alt: "Images are built in layers; identical layers are reused from the build cache", demo: "Concept" },
    {
      title: "Containerising a FastAPI + LangChain App",
      subtitle: "One container: request → LLM call → response",
      demo: M + "1_fastapi_langchain/",
      split: [1.1, 1],
      left: [
        { type: "code", caption: "Build and run", code:
`cd 14_advanced/18_Dockerizing/1_fastapi_langchain
docker build -t fastapi-langchain-demo .
docker run -d --name fastapi-langchain-demo ^
  -p 8000:8000 --env-file .env fastapi-langchain-demo` },
        { type: "code", caption: "Try it", code:
`GET  http://localhost:8000/health
POST http://localhost:8000/summarize
     {"text": "some text to summarize"}` },
      ],
      right: [
        { type: "icons", d: 0.36, size: 11, items: [
          { icon: "FaFileShield", title: "--env-file .env", text: "Keys are passed in at run time, never baked into the image" },
          { icon: "FaHeartPulse", title: "HEALTHCHECK on /health", text: "Deliberately doesn't call the LLM – it reports whether the process is serving" },
          { icon: "FaUserLock", title: "Non-root user", text: "Limits the damage if the app is compromised" },
        ] },
      ],
    },
    {
      title: "Multi-Stage Builds",
      subtitle: "Build tools are needed to install packages, not to run them – so leave them behind",
      demo: M + "1_fastapi_langchain/Dockerfile",
      split: [1.25, 1],
      left: [
        { type: "code", caption: "Dockerfile (condensed)", code:
`# ---- Stage 1: builder ----
FROM python:3.12-slim AS builder
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY requirements.txt .          # before the code → cache
RUN pip install --no-cache-dir -r requirements.txt

# ---- Stage 2: runtime ----
FROM python:3.12-slim AS runtime
RUN useradd --uid 1000 --create-home appuser
COPY --from=builder /opt/venv /opt/venv
COPY app ./app
USER appuser
HEALTHCHECK CMD python -c "...urlopen('.../health')"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]` },
      ],
      right: [
        { type: "tree", boxW: 2.3, size: 10, boxH: 0.42, labels: ["copy only what's needed"], rows: [[{ label: "Build stage: compilers, pip, dev deps", fill: "slate" }], [{ label: "Runtime stage: small base + venv + app", fill: "teal" }]] },
        { type: "bullets", size: 10.5, items: [
          "A smaller image – faster to pull and start",
          "Fewer tools inside – a smaller attack surface",
          "requirements.txt copied first, so code edits skip the pip layer",
        ] },
      ],
    },
    {
      title: "Docker Compose: API + MySQL",
      subtitle: "Run several containers as one application stack – services, networks and volumes in one file",
      demo: M + "2_fastapi_langchain_mysql_history/  ·  docker compose up -d --build",
      split: [1, 1.1],
      left: [
        { type: "tree", boxW: 1.5, size: 10.5, rows: [[{ label: "docker-compose.yml", fill: "navy" }], ["api (FastAPI)", "mysql"], [{ label: "Shared network · mysql_data volume", fill: "teal" }]] },
        { type: "text", size: 11, color: "slate", text: "Each summary is stored in MySQL; GET /history reads them back. MySQL has no published port – only the API can reach it." },
      ],
      right: [
        { type: "code", caption: "Check the data is there", code:
`docker exec -it mysql_container mysql -u app -p
# password: app_password
use summarizer;
select * from summaries;` },
        { type: "icons", d: 0.34, size: 10.5, items: [
          { icon: "FaServer", title: "Services", text: "One per container" },
          { icon: "FaNetworkWired", title: "Networks", text: "Services find each other by name" },
          { icon: "FaHardDrive", title: "Volumes", text: "Data that outlives the containers" },
        ] },
      ],
    },
    {
      title: "A Full Agent Stack with a Job Queue",
      subtitle: "Four containers – the API only queues work; workers do it, and scale independently",
      demo: M + "3_fastapi_chromadb_redis_worker/",
      blocks: [
        { type: "flow", items: [
          { icon: "FaUser", label: "Client", caption: "POST /ask → job_id" },
          { icon: "FaServer", label: "api", caption: "FastAPI – only talks to Redis" },
          { icon: "FaListOl", label: "redis", caption: "Job queue and job status", color: "coral" },
          { icon: "FaGears", label: "worker", caption: "Embeds, queries ChromaDB, calls the LLM", color: "teal" },
          { icon: "FaDatabase", label: "chromadb", caption: "One shared vector store" },
        ] },
        { type: "cols", cols: [
          [{ type: "code", caption: "Scale the workers – no code changes", code: `docker compose up -d --scale worker=3` }],
          [{ type: "text", size: 11, text: "The client polls `GET /jobs/{job_id}` until the job is **done**. `api` and `worker` are the same image with a different `command:`." }],
        ] },
      ],
    },
    {
      title: "A Full-Stack App: Streamlit + FastAPI",
      subtitle: "Two images, one compose file – only the UI is published to the outside world",
      demo: M + "4_streamlit_fastapi_fullstack/  ·  docker compose up -d --build  →  localhost:8501",
      split: [1, 1.05],
      left: [
        { type: "flow", items: [
          { icon: "FaUser", label: "Browser", caption: "localhost:8501" },
          { icon: "FaDesktop", label: "frontend", caption: "Streamlit UI", color: "teal" },
          { icon: "FaServer", label: "backend", caption: "FastAPI /ask", color: "coral" },
          { icon: "FaMicrochip", label: "OpenAI", caption: "gpt-4o-mini" },
        ] },
        { type: "bullets", size: 11, items: [
          "**Service names are host names:** the UI calls `http://backend:8000` – inside its container, `localhost` is the UI itself",
          "**Publish only what users need:** no `ports:` on the backend; the API key lives only there",
          "**Start in order:** the UI waits until the backend's `/health` passes",
        ] },
      ],
      right: [
        { type: "code", caption: "docker-compose.yml (condensed)", code:
`services:
  backend:
    build: ./backend
    env_file: [.env]          # OPENAI_API_KEY
    # no ports: - internal only

  frontend:
    build: ./frontend
    ports: ["8501:8501"]
    environment:
      - BACKEND_URL=http://backend:8000
    depends_on:
      backend:
        condition: service_healthy` },
      ],
    },
    {
      title: "Run It on AWS: Launch an EC2 Instance",
      subtitle: "The simplest path – one virtual machine running the same docker compose command",
      demo: FS + "README.md  →  Run it on AWS (EC2)",
      split: [1.15, 1],
      left: [
        { type: "table", size: 10.5, widths: [1.5, 3.1], head: ["Setting", "Value"], rows: [
          ["AMI", "Ubuntu Server 24.04 LTS"],
          ["Instance type", "t3.small – 2 GB RAM runs both containers"],
          ["Key pair", "Create one; download the .pem file"],
          ["Security group", "SSH 22 and TCP 8501 – both from My IP"],
          ["Storage", "20 GB gp3"],
        ] },
      ],
      right: [
        { type: "steps", size: 10.5, items: [
          { title: "EC2 console → Launch instance", text: "Use the settings on the left" },
          { title: "Do not open port 8000", text: "The backend stays private, exactly as on your laptop" },
          { title: "Note the public IP", text: "It changes on stop/start – use an Elastic IP to keep it" },
        ] },
        { type: "callout", eyebrow: "Cost", text: "Stop or terminate the instance when you are done – a running VM is billed by the second." },
      ],
    },
    {
      title: "Run It on AWS: Deploy with Compose",
      subtitle: "Install Docker, clone the repo, add the key, start the stack",
      demo: FS + "  ·  http://<public-ip>:8501",
      split: [1.3, 1],
      left: [
        { type: "code", caption: "On the instance (ssh -i my-key.pem ubuntu@<public-ip>)", code:
`# 1. Docker Engine + buildx + compose plugin
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker ubuntu   # then log out and in

# 2. Code and secret
git clone https://github.com/atulkahatecdac/agenticai.git
cd agenticai/14_advanced/18_Dockerizing
cd 4_streamlit_fastapi_fullstack
cp .env.example .env && nano .env   # OPENAI_API_KEY
chmod 600 .env

# 3. Start
docker compose up -d --build
docker compose ps        # both "healthy"` },
      ],
      right: [
        { type: "steps", size: 10.5, items: [
          { title: "Open http://<public-ip>:8501", text: "The same UI as on your laptop" },
          { title: "Survives reboots", text: "`restart: unless-stopped` + Docker starts on boot" },
          { title: "Update", text: "`git pull && docker compose up -d --build`" },
          { title: "Clean up", text: "`docker compose down`, then stop or terminate the instance" },
        ] },
      ],
    },
    {
      title: "From Demo to Production on AWS",
      subtitle: "Same containers – what changes when real users depend on them",
      demo: "Concept",
      blocks: [
        { type: "table", size: 10.5, widths: [1.4, 2.6, 3.6], head: ["Concern", "EC2 demo", "Production"], rows: [
          ["Secrets", ".env file on the VM", "AWS Secrets Manager or SSM Parameter Store, injected at start"],
          ["Images", "Built on the VM", "Built in CI, pushed to Amazon ECR"],
          ["Running", "One VM, docker compose", "ECS on Fargate – one service per container – or App Runner"],
          ["HTTPS", "Plain HTTP on 8501", "Application Load Balancer + ACM certificate, port 443 only"],
          ["Address", "Public IP", "Elastic IP or a Route 53 domain"],
          ["Updates", "git pull, rebuild", "Blue/green or canary releases – next"],
        ] },
      ],
    },
    {
      title: "Blue/Green Deployment",
      subtitle: "Run the old and new versions side by side, then switch traffic all at once",
      demo: "Concept",
      split: [1, 1.1],
      left: [
        { type: "tree", boxW: 1.7, size: 10, boxH: 0.36, gapY: 0.24, rows: [["Load balancer"], [{ label: "BLUE v1.0 (live)", fill: "navy" }, { label: "GREEN v2.0 (testing)", fill: "teal" }], ["Switch traffic → GREEN"]] },
      ],
      right: [
        { type: "steps", size: 10.5, gap: 0.07, items: [
          { title: "Blue runs the current production version" },
          { title: "Deploy the new version to Green" },
          { title: "Test Green while users stay on Blue" },
          { title: "Switch the load balancer to Green" },
          { title: "Keep Blue ready for an instant rollback" },
        ] },
      ],
    },
    {
      title: "Canary Deployment",
      subtitle: "Release the new agent to a small share of users first, and widen it while it behaves",
      demo: "Concept",
      split: [1.1, 1],
      left: [
        { type: "table", size: 10.5, widths: [1.4, 1.2, 1.2], head: ["Stage", "Agent v1.0", "Agent v2.0"], rows: [
          ["Initial", "100%", "0%"],
          ["Canary", "95%", "5%"],
          ["Expand", "90%", "10%"],
          ["Expand", "75%", "25%"],
          ["Expand", "50%", "50%"],
          ["Complete", "0%", "100%"],
        ] },
      ],
      right: [
        { type: "text", text: "**Watch the canary for**", size: 12 },
        { type: "tiles", cols: 2, size: 10, titleSize: 11, items: [
          { icon: "FaBug", title: "Errors" },
          { icon: "FaGaugeHigh", title: "Latency" },
          { icon: "FaStar", title: "Answer quality" },
          { icon: "FaShieldHalved", title: "Safety" },
        ] },
        { type: "callout", eyebrow: "For agents", text: "Quality and safety matter as much as errors – a new prompt can fail silently." },
      ],
    },
    {
      kind: "summary",
      title: "Module 18 Summary",
      subtitle: "What you built",
      built: [
        { tag: "1", title: "One container", text: "FastAPI + LangChain, multi-stage, non-root" },
        { tag: "2", title: "Two containers", text: "API + MySQL history with Compose" },
        { tag: "3", title: "Four containers", text: "API, worker, Redis queue, ChromaDB" },
        { tag: "4", title: "A full stack on AWS", text: "Streamlit + FastAPI with Compose, on EC2" },
        { tag: "ship", title: "Safe releases", text: "Blue/green and canary strategies" },
      ],
      takeaways: [
        "Images are layers – order the Dockerfile for caching",
        "Build in one stage, run in a slim one",
        "Pass secrets at run time, never in the image",
        "Queue slow LLM work; scale workers separately",
        "Release gradually and keep a rollback ready",
      ],
      next: "Module 19: Capstone Projects",
    },
  ],
};
