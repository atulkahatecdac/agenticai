# The backend API. Run locally from this folder:
#   uvicorn main:app --port 8022 --reload
from dotenv import load_dotenv

load_dotenv(override=True)   # on a laptop: reads ../.env  (in Docker there is no .env file)

from fastapi import FastAPI, HTTPException, UploadFile   # noqa: E402  (after load_dotenv)
from pydantic import BaseModel            # noqa: E402

import agent      # noqa: E402
import database   # noqa: E402
import rag        # noqa: E402

app = FastAPI(title="DocAssist API")
database.create_tables()


class ChatIn(BaseModel):
    session_id: str
    question: str


@app.get("/health")
def health():
    with database.connect() as conn:   # healthy = Postgres answers
        conn.execute("SELECT 1")
    return {"status": "ok"}


@app.post("/documents")
def upload(file: UploadFile):
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(400, "Please upload a PDF file")
    chunks = rag.add_document(file.filename, file.file)
    return {"document": file.filename, "chunks": chunks}


@app.get("/documents")
def documents():
    return {"documents": database.list_sources()}


@app.post("/chat")
def chat(body: ChatIn):
    reply, steps = agent.answer(body.session_id, body.question)
    return {"reply": reply, "steps": steps}


@app.get("/history/{session_id}")
def history(session_id: str):
    return {"messages": database.load_history(session_id, limit=100)}
