// DEMO paths are relative to 14_advanced/19_capstone/docassist/
module.exports = {
  section: "Introduction",
  slides: [
    {
      kind: "cover",
      eyebrow: "Capstone",
      title: "DocAssist",
      description: "An Agentic RAG app with memory in Postgres – built step by step, then deployed to the cloud with Docker Compose.",
      author: "Atul Kahate",
      authorLink: "linkedin.com/in/atulkahate",
      repo: "github.com/atulkahatecdac/agenticai",
      footnote: "Code: 14_advanced/19_capstone/docassist",
      journey: [
        { icon: "FaFilePdf", title: "RAG", text: "PDFs → chunks → embeddings in pgvector" },
        { icon: "FaRobot", title: "Agentic RAG", text: "The model decides when to search" },
        { icon: "FaDatabase", title: "Memory in Postgres", text: "Survives restarts" },
        { icon: "FaDocker", title: "Docker Compose", text: "Frontend, backend, database" },
        { icon: "FaCloud", title: "Cloud VM", text: "A public URL you can show" },
      ],
    },
    {
      title: "What We Build",
      subtitle: "Three containers – only the frontend is reachable from outside",
      demo: "README.md",
      blocks: [
        { type: "flow", items: [
          { icon: "FaUser", label: "Browser", caption: "http://<server>:8522" },
          { icon: "FaDesktop", label: "frontend", caption: "Streamlit: upload PDFs, chat", color: "teal" },
          { icon: "FaServer", label: "backend", caption: "FastAPI: the agent, RAG, memory", color: "coral" },
          { icon: "FaDatabase", label: "db", caption: "Postgres + pgvector: chunks and messages" },
        ] },
        { type: "table", size: 10.5, widths: [1.4, 3.2, 3.2], head: ["Container", "Knows", "Does not know"], rows: [
          ["frontend", "BACKEND_URL", "the OpenAI key, the database"],
          ["backend", "OPENAI_API_KEY, DATABASE_URL", "–  (the only one that calls OpenAI)"],
          ["db", "POSTGRES_PASSWORD", "anything about AI"],
        ] },
      ],
    },
    {
      title: "The Steps",
      subtitle: "Small scripts first, one idea each – then the real app built from the same pieces",
      demo: "README.md  →  The steps",
      blocks: [
        { type: "table", size: 10, widths: [0.6, 2.3, 5.1], head: ["Step", "File", "What it adds"], rows: [
          ["01", "01a_embeddings.py", "Text → 1536 numbers; similar meaning = similar numbers"],
          ["02", "02a_pgvector.py", "Store embeddings in Postgres, find the nearest with `<=>`"],
          ["02", "02b_ingest_pdfs.py", "PDFs → chunks → embeddings → the `chunks` table"],
          ["03", "03a_rag.py", "Plain RAG: always search, then answer"],
          ["04", "04a_agentic_rag.py", "Agentic RAG: search is a tool the model decides to use"],
          ["05", "05a_memory.py", "Short-term memory in a `messages` table"],
          ["06", "backend/", "FastAPI: upload, chat, history, health"],
          ["07", "frontend/app.py", "Streamlit chat UI"],
          ["08", "docker-compose.yml", "The three containers together"],
          ["09", "README.md", "Deploy on a cloud VM"],
        ] },
      ],
    },
    {
      title: "Setup",
      subtitle: "A .env file for the settings, and one Postgres container for steps 02–07",
      demo: ".env.example",
      split: [1.15, 1],
      left: [
        { type: "code", caption: "terminal (in the docassist folder)", code:
"cp .env.example .env\n\ndocker run -d --name docassist-db \\\n  -e POSTGRES_PASSWORD=docassist123 \\\n  -e POSTGRES_DB=docassist \\\n  -p 5433:5432 pgvector/pgvector:pg17" },
        { type: "code", caption: ".env", size: 8, code:
"OPENAI_API_KEY=sk-...\nPOSTGRES_PASSWORD=docassist123\nDATABASE_URL=postgresql://postgres:docassist123@localhost:5433/docassist" },
      ],
      right: [
        { type: "icons", items: [
          { icon: "FaDatabase", title: "pgvector/pgvector:pg17", text: "Official Postgres image with the vector extension added" },
          { icon: "FaPlug", title: "Port 5433", text: "Avoids a Postgres you may already run on 5432" },
          { icon: "FaKey", title: "Settings live in .env", text: "Never in the code. `.env` is git-ignored" },
          { icon: "FaLink", title: "DATABASE_URL", text: "user : password @ host : port / database" },
        ] },
      ],
    },
  ],
};
