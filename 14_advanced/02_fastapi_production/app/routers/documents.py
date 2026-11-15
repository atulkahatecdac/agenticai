"""/documents - upload a file, get a summary back. Needs the X-API-Key header (set in main.py)."""
import io

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from langchain_core.language_models import BaseChatModel
from pydantic import BaseModel
from pypdf import PdfReader

from app.config import Settings, get_settings
from app.dependencies import get_llm

router = APIRouter(prefix="/documents", tags=["documents"])

ALLOWED = {"text/plain", "application/pdf"}


class SummaryResponse(BaseModel):
    filename: str
    characters: int
    summary: str


def extract_text(data: bytes, content_type: str) -> str:
    if content_type == "application/pdf":
        reader = PdfReader(io.BytesIO(data))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    return data.decode("utf-8", errors="replace")


@router.post("/summarize", response_model=SummaryResponse)
async def summarize(
    file: UploadFile,                                  # multipart/form-data field named "file"
    llm: BaseChatModel = Depends(get_llm),
    settings: Settings = Depends(get_settings),
) -> SummaryResponse:
    # 1. Check the type and size BEFORE doing any work on the file.
    if file.content_type not in ALLOWED:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, f"Upload .txt or .pdf, not {file.content_type}")
    data = await file.read()
    if len(data) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, f"File is over {settings.max_upload_mb} MB")

    # 2. File -> text -> LLM. Long files are cut to keep the prompt small (Module 04/05 chunk them instead).
    text = extract_text(data, file.content_type).strip()
    if not text:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "No text found in the file")
    prompt = f"Summarise this document in 3 bullet points:\n\n{text[:12000]}"
    result = await llm.ainvoke(prompt)
    return SummaryResponse(filename=file.filename, characters=len(text), summary=result.content)
