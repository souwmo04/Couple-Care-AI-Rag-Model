"""Chat endpoints: JSON (``POST /api/chat``) and streaming SSE (``POST /api/chat/stream``)."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.api.deps import get_container, get_owner
from app.core.container import Container
from app.core.orchestrator import Orchestrator
from app.core.schemas import ChatRequest, ChatResponse

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(
    body: ChatRequest, owner: str = Depends(get_owner), c: Container = Depends(get_container)
) -> ChatResponse:
    return await Orchestrator(c).respond(body, owner)


def _sse(event: dict) -> str:
    name = event.get("event", "message")
    return f"event: {name}\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"


@router.post("/chat/stream")
async def chat_stream(body: ChatRequest, owner: str = Depends(get_owner), c: Container = Depends(get_container)):
    events = Orchestrator(c).stream(body, owner)
    # Pull the first event eagerly so validation / not-found errors are returned as proper
    # HTTP errors rather than failing inside an already-started stream.
    first = await anext(events)

    async def body_iter() -> AsyncIterator[str]:
        yield _sse(first)
        async for event in events:
            yield _sse(event)

    return StreamingResponse(
        body_iter(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
    )
