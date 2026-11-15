"""Step 1: the whole API in one file. Read this first; app/ is the same API split up for a bigger team.

Run from 14_advanced/02_fastapi_production:
    uvicorn simple_main:app --reload        -> http://localhost:8000/docs

Endpoints:
    GET  /health      is the server up?
    POST /chat        {"message": "..."}  ->  {"reply": "..."}
    POST /summarize   upload a .txt file  ->  {"summary": "..."}
"""
import os

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, UploadFile
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, "..", "..", ".env"), override=True)

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)      # created once, shared by every request

app = FastAPI(title="Simple Agent API")


# 1. Pydantic models describe the JSON coming in and going out (FastAPI checks it for you).
class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    result = llm.invoke(req.message)
    return ChatResponse(reply=result.content)


# 2. UploadFile receives a file sent as a form upload (not JSON).
@app.post("/summarize")
async def summarize(file: UploadFile):
    if file.content_type != "text/plain":
        raise HTTPException(status_code=415, detail="Please upload a .txt file")
    data = await file.read()
    if len(data) > 1_000_000:                      # check size BEFORE paying for an LLM call
        raise HTTPException(status_code=413, detail="File is over 1 MB")
    text = data.decode("utf-8", errors="replace")
    result = llm.invoke(f"Summarise this in 3 bullet points:\n\n{text[:12000]}")
    return {"filename": file.filename, "summary": result.content}
