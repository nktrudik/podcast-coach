from typing import Annotated

from fastapi import APIRouter, Depends, Path

from app.api.dependencies import get_settings
from app.api.errors import APIConflictError, APINotFoundError
from app.api.schemas import (
    ChatMessageItem,
    ChatSessionItem,
    SendMessageRequest,
    SendMessageResponse,
    StartChatRequest,
    StartChatResponse,
)
from app.clients.llm import ask_llm
from app.core.config import Settings
from app.core.logger import get_logger
from app.db.repositories.messages import add_message, get_messages
from app.db.repositories.sessions import (
    count_chat_sessions_by_video,
    create_chat_session,
    get_chat_session,
    list_chat_sessions,
)
from app.db.repositories.videos import get_video

router = APIRouter(prefix="/chat")
logger = get_logger(__name__)


@router.post("/start")
def start_chat(
    payload: StartChatRequest,
    app_settings: Annotated[Settings, Depends(get_settings)],
) -> StartChatResponse:
    """Создает чат-сессию для выбранного видео."""
    video = get_video(payload.video_id)
    if not video:
        raise APINotFoundError("Видео не найдено")

    sessions_total = count_chat_sessions_by_video(payload.video_id)
    if sessions_total >= app_settings.chat_sessions_per_video_limit:
        raise APIConflictError(
            "Для одного видео можно создать не больше "
            f"{app_settings.chat_sessions_per_video_limit} чатов. "
            "Продолжи существующий чат или удали один из старых.",
        )

    session_id = create_chat_session(payload.video_id)
    logger.info("Создана чат-сессия: session_id=%s, video_id=%s", session_id, payload.video_id)

    return StartChatResponse(session_id=session_id)


@router.post("/message")
def send_message(
    payload: SendMessageRequest,
    app_settings: Annotated[Settings, Depends(get_settings)],
) -> SendMessageResponse:
    """Отправляет сообщение в чат и возвращает ответ ассистента."""
    session = get_chat_session(payload.session_id)
    if not session:
        raise APINotFoundError("Чат-сессия не найдена")

    video_id = session.get("video_id")
    if video_id is None:
        raise APIConflictError("К сессии не привязано видео")

    video = get_video(video_id)
    if not video:
        raise APINotFoundError("Видео не найдено")

    transcript = video["transcript"]
    if not isinstance(transcript, str) or not transcript.strip():
        raise APIConflictError("Транскрипт для видео отсутствует")

    memory = get_messages(
        payload.session_id,
        limit=app_settings.llm_memory_messages_limit,
    )

    system_prompt = f"""
        You are an English speaking coach.

        Here is the podcast transcript:
        {transcript}
    """

    logger.info("Получен запрос сообщения в сессии: session_id=%s", payload.session_id)
    answer, _ = ask_llm(system_prompt, payload.message, memory)

    add_message(payload.session_id, "user", payload.message)
    add_message(payload.session_id, "assistant", answer)
    logger.info("Ответ ассистента сохранен: session_id=%s", payload.session_id)

    return SendMessageResponse(answer=answer)


@router.get("/sessions", response_model=list[ChatSessionItem])
def get_sessions() -> list[ChatSessionItem]:
    """Возвращает список созданных чат-сессий."""
    return [ChatSessionItem(**session) for session in list_chat_sessions()]


@router.get("/sessions/{session_id}/messages", response_model=list[ChatMessageItem])
def get_session_messages(session_id: Annotated[int, Path(gt=0)]) -> list[ChatMessageItem]:
    """Возвращает историю сообщений конкретной чат-сессии."""
    session = get_chat_session(session_id)
    if not session:
        raise APINotFoundError("Чат-сессия не найдена")

    history = get_messages(session_id)
    return [ChatMessageItem(**message) for message in history]
