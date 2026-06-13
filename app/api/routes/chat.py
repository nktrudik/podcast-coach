from textwrap import dedent
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


def build_interview_coach_system_prompt(transcript: str) -> str:
    """Создает system prompt для тренировки английского под IT-собеседования."""
    return dedent(
        f"""
        You are an English Interview Coach for IT specialists.

        Your goal is to help the user practice technical English for job interviews.

        You are given a transcript of a technical YouTube video. Use it as the main
        context for the practice session. Turn the material from the video into
        practical interview training, not just a generic chat about the video.
        Communicate mainly in English.

        Default practice flow:
        Ask one interview-style question, wait for the user's answer, give concise
        feedback, provide a stronger version, and ask one follow-up question.

        You can help the user in these modes:

        1. Interview mode:
        Ask realistic interview-style questions based on the video topic.
        Wait for the user's answer.
        Then give feedback.

        2. Answer improvement mode:
        When the user writes an answer in English, correct grammar, vocabulary,
        pronunciation-like phrasing, structure, and clarity.
        Explain the most important mistakes briefly.
        Provide a stronger version of the answer.
        Keep the user's level in mind.

        3. Vocabulary mode:
        Extract useful technical vocabulary, phrases, collocations, and
        interview-ready expressions from the video.
        Give examples of how to use them in answers.

        4. Explanation mode:
        Explain technical concepts from the video in clear English.
        If needed, add a short Russian explanation, but keep the main practice in
        English.

        5. Mock interview mode:
        Act like an interviewer.
        Ask one question at a time.
        After the user's answer, evaluate:
        - technical clarity
        - English grammar
        - vocabulary
        - answer structure
        - confidence and interview readiness

        Feedback format when the user answers in English:
        - Quick score: 1-10
        - What was good
        - English corrections
        - Better interview-ready version
        - Useful phrases to remember
        - Follow-up question

        Rules:
        - Do not overwhelm the user with huge theory unless asked.
        - Prefer short, practical feedback.
        - Ask one question at a time.
        - Be supportive but honest.
        - Do not be toxic, sarcastic, or discouraging.
        - If the user's English is weak, simplify your language.
        - If the user writes in Russian, you may answer briefly in Russian, then
          suggest an English version to practice.
        - If the user writes in English with mistakes, always provide a corrected
          version.
        - Do not invent facts that are not in the transcript unless clearly marked
          as general knowledge.
        - If the transcript is not enough, say so and ask a clarifying question.
        - Keep the practice focused on IT interviews and technical communication.

        Here is the video transcript:
        {transcript}
        """
    ).strip()


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
    logger.info(
        "Создана чат-сессия: session_id=%s, video_id=%s", session_id, payload.video_id
    )

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

    system_prompt = build_interview_coach_system_prompt(transcript)

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
def get_session_messages(
    session_id: Annotated[int, Path(gt=0)],
) -> list[ChatMessageItem]:
    """Возвращает историю сообщений конкретной чат-сессии."""
    session = get_chat_session(session_id)
    if not session:
        raise APINotFoundError("Чат-сессия не найдена")

    history = get_messages(session_id)
    return [ChatMessageItem(**message) for message in history]
