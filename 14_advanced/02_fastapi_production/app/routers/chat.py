"""/chat - one router per area of the API keeps main.py tiny."""
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from langchain_core.language_models import BaseChatModel
from pydantic import BaseModel, Field

from app.dependencies import get_llm

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


class ChatResponse(BaseModel):
    reply: str


@router.post("", response_model=ChatResponse)
async def chat(req: ChatRequest, llm: BaseChatModel = Depends(get_llm)) -> ChatResponse:
    result = await llm.ainvoke(req.message)
    return ChatResponse(reply=result.content)


@router.post("/stream")
async def chat_stream(req: ChatRequest, llm: BaseChatModel = Depends(get_llm)):
    """Server-Sent Events: one `data:` line per chunk, then [DONE]."""
    async def events():
        async for chunk in llm.astream(req.message):
            if chunk.content:
                yield f"data: {chunk.content}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(events(), media_type="text/event-stream")
