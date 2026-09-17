from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class IngestRequest(BaseModel):
    doc_id: str = Field(..., min_length=1, description="Unique identifier for this document.")
    text: str = Field(..., min_length=1, max_length=50_000)


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2_000)


class JobAccepted(BaseModel):
    job_id: str


JobStatus = Literal["pending", "done", "error"]


class JobStatusResponse(BaseModel):
    job_id: str
    status: JobStatus
    result: Optional[Any] = None
