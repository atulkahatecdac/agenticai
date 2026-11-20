module.exports = {
  section: "The App",
  slides: [
    {
      title: "06 – The Backend (FastAPI)",
      subtitle: "Steps 02–05, split into four small files",
      demo: "backend/  →  uvicorn main:app --port 8022 --reload",
      split: [1, 1],
      left: [
        { type: "table", size: 10.5, widths: [1.3, 2.8], head: ["File", "What it holds"], rows: [
          ["database.py", "All SQL: tables, chunks, nearest_chunks, memory"],
          ["rag.py", "PDF → chunks → embeddings, search"],
          ["agent.py", "The tool loop from 04a + the memory from 05a"],
          ["main.py", "The HTTP endpoints"],
        ] },
        { type: "callout", eyebrow: "Same code everywhere", text: "`DATABASE_URL` decides where Postgres is: localhost:5433 on a laptop, db:5432 in Compose." },
      ],
      right: [
        { type: "table", size: 10.5, widths: [2.1, 2.1], head: ["Endpoint", "Does"], rows: [
          ["POST /documents", "Upload a PDF → chunks"],
          ["GET /documents", "List the documents"],
          ["POST /chat", "session_id + question → reply + steps"],
          ["GET /history/{id}", "The conversation, from Postgres"],
          ["GET /health", "OK only if Postgres answers"],
        ] },
      ],
    },
    {
      title: "07 – The Frontend (Streamlit)",
      subtitle: "Only talks to the backend over HTTP – it never sees the OpenAI key or the database",
      demo: "frontend/app.py  →  streamlit run app.py --server.port 8522",
      split: [1, 1.35],
      left: [
        { type: "code", caption: "frontend/app.py", size: 9, code:
"BACKEND_URL = os.environ.get(\n    \"BACKEND_URL\", \"http://localhost:8022\")\n\nif \"sid\" not in st.query_params:\n    st.query_params[\"sid\"] = \\\n        uuid.uuid4().hex[:8]\nsession_id = st.query_params[\"sid\"]\n\nhistory = requests.get(\n    f\"{BACKEND_URL}/history/{session_id}\"\n).json()[\"messages\"]" },
        { type: "bullets", size: 10.5, items: [
          "Session id in the URL: a refresh keeps the conversation",
          "History comes from Postgres, not from the browser",
          "\"Agent: searched ...\" shows what the agent did",
        ] },
      ],
      right: [
        { type: "image", src: "docassist_ui.png", alt: "DocAssist chat UI" },
      ],
    },
  ],
};
