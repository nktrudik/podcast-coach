from typing import Annotated

from fastapi import APIRouter, Depends, Path

from app.api.errors import APINotFoundError
from app.api.schemas import (
    ChatMessageItem,
    ChatSessionItem,
    SendMessageRequest,
    SendMessageResponse,
    StartChatRequest,
    StartChatResponse,
)
from app.db.repositories.messages import get_messages
from app.db.repositories.sessions import get_chat_session, list_chat_sessions
from app.services.chat import ChatService, get_chat_service

router = APIRouter(prefix="/chat")


@router.post("/start", response_model=StartChatResponse)
def start_chat(
    payload: StartChatRequest,
    service: Annotated[ChatService, Depends(get_chat_service)],
) -> StartChatResponse:
    """Create a chat session for a selected video."""
    session_id = service.start_chat(payload.video_id)
    return StartChatResponse(session_id=session_id)


@router.post("/message", response_model=SendMessageResponse)
def send_message(
    payload: SendMessageRequest,
    service: Annotated[ChatService, Depends(get_chat_service)],
) -> SendMessageResponse:
    """Send a chat message and return the assistant answer."""
    answer = service.send_message(payload.session_id, payload.message)
    return SendMessageResponse(answer=answer.answer)


@router.get("/sessions", response_model=list[ChatSessionItem])
def get_sessions() -> list[ChatSessionItem]:
    """Return created chat sessions."""
    return [ChatSessionItem(**session) for session in list_chat_sessions()]


@router.get("/sessions/{session_id}/messages", response_model=list[ChatMessageItem])
def get_session_messages(
    session_id: Annotated[int, Path(gt=0)],
) -> list[ChatMessageItem]:
    """Return message history for a chat session."""
    session = get_chat_session(session_id)
    if not session:
        raise APINotFoundError("Chat session was not found")

    history = get_messages(session_id)
    return [ChatMessageItem(**message) for message in history]
