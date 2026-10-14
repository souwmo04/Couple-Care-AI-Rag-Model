"""Conversation history endpoints. Only the requesting client's conversations are visible."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Path, Query, Response

from app.api.deps import get_container, get_owner
from app.core.container import Container
from app.core.schemas import (
    CONVERSATION_ID_PATTERN,
    ConversationDetail,
    ConversationList,
    DeleteAllRequest,
    FeedbackRequest,
)
from app.errors import NotFoundError

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


@router.get("", response_model=ConversationList)
async def list_conversations(
    q: str | None = Query(default=None, max_length=100),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    owner: str = Depends(get_owner),
    c: Container = Depends(get_container),
) -> ConversationList:
    store = c.store()
    items, total = store.list(owner, q.strip() if q else None, limit, offset)
    return ConversationList(persistence_enabled=store.persistent, items=[i.summary() for i in items], total=total)


@router.get("/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(
    conversation_id: str = Path(pattern=CONVERSATION_ID_PATTERN),
    owner: str = Depends(get_owner),
    c: Container = Depends(get_container),
) -> ConversationDetail:
    conv = c.store().get(owner, conversation_id)
    if conv is None:
        raise NotFoundError("Conversation not found.")
    return conv.detail()


@router.delete("/{conversation_id}", status_code=204)
async def delete_conversation(
    conversation_id: str = Path(pattern=CONVERSATION_ID_PATTERN),
    owner: str = Depends(get_owner),
    c: Container = Depends(get_container),
) -> Response:
    deleted = c.memory_store.delete(owner, conversation_id)
    sqlite = c.sqlite_if_exists()
    if sqlite is not None:
        deleted = sqlite.delete(owner, conversation_id) or deleted
    if not deleted:
        raise NotFoundError("Conversation not found.")
    return Response(status_code=204)


@router.delete("")
async def delete_all_conversations(
    body: DeleteAllRequest, owner: str = Depends(get_owner), c: Container = Depends(get_container)
) -> dict:
    """Delete every conversation for this client, from memory and from disk.

    Requires ``{"confirm": "DELETE ALL"}`` in the body as explicit confirmation.
    """
    count = c.memory_store.delete_all(owner)
    sqlite = c.sqlite_if_exists()
    if sqlite is not None:
        count += sqlite.delete_all(owner)
    return {"deleted": count}


@router.post("/{conversation_id}/messages/{message_id}/feedback", status_code=204)
async def message_feedback(
    body: FeedbackRequest,
    conversation_id: str = Path(pattern=CONVERSATION_ID_PATTERN),
    message_id: str = Path(pattern=CONVERSATION_ID_PATTERN),
    owner: str = Depends(get_owner),
    c: Container = Depends(get_container),
) -> Response:
    if not c.store().set_feedback(owner, conversation_id, message_id, body.rating):
        raise NotFoundError("Message not found.")
    return Response(status_code=204)
