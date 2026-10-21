const M = "18_Dockerizing/";

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
        { icon: "FaLayerGroup", title: "Compose multi-container stacks", text: "API + MySQL; API + worker + Redis + ChromaDB" },
        { icon: "FaCodeBranch", title: "Release without downtime", text: "blue/green and canary deployments" },
      ],
      agenda: [
        "Docker key terms",
        "A FastAPI + LangChain image",
        "Multi-stage builds",
        "Docker Compose: API + MySQL",
        "A full agent stack with a worker queue",
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
