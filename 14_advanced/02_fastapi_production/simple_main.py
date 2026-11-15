"""Step 1: the whole API in one file. Read this first; app/ is the same API split up for a bigger team.

Run from 14_advanced/02_fastapi_production:
    uvicorn simple_main:app --reload        -> http://localhost:8000/docs

Endpoints:
    GET  /health      is the server up?
    POST /chat        {"message": "..."}  ->  {"reply": "..."}
    POST /summarize   upload a .txt file (needs the X-API-Key header)  ->  {"summary": "..."}
"""
import os

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException, UploadFile
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, "..", "..", ".env"), override=True)

API_KEY = os.getenv("APP_API_KEY", "dev-key-change-me")  # protects YOUR API; not the OpenAI key
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)      # created once, shared by every request

app = FastAPI(title="Simple Agent API")


# 1. Pydantic models describe the JSON coming in and going out (FastAPI checks it for you).
class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str


# 2. A dependency: FastAPI runs it before the endpoint. If it raises, the endpoint never runs.
def check_key(x_api_key: str = Header(default="")):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Missing or wrong X-API-Key header")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    result = llm.invoke(req.message)
    return ChatResponse(reply=result.content)


# 3. UploadFile receives a file; Depends(check_key) protects just this endpoint.
@app.post("/summarize", dependencies=[Depends(check_key)])
async def summarize(file: UploadFile):
    if file.content_type != "text/plain":
        raise HTTPException(status_code=415, detail="Please upload a .txt file")
    data = await file.read()
    if len(data) > 1_000_000:                      # check size BEFORE paying for an LLM call
        raise HTTPException(status_code=413, detail="File is over 1 MB")
    text = data.decode("utf-8", errors="replace")
    result = llm.invoke(f"Summarise this in 3 bullet points:\n\n{text[:12000]}")
    return {"filename": file.filename, "summary": result.content}
