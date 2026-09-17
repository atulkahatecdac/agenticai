from pydantic import BaseModel, Field


class SummarizeRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=20_000, description="Text to summarize.")


class SummarizeResponse(BaseModel):
    summary: str
