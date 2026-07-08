from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from textwrap import dedent

from app.clients.llm import MemoryMessage, ask_llm
from app.core.config import Settings, settings
from app.core.logger import get_logger
from app.core.status import VideoStatus
from app.core.types import DatabaseRecord
from app.db.repositories.messages import add_message, get_messages
from app.db.repositories.sessions import (
    count_chat_sessions_by_video,
    create_chat_session,
    get_chat_session,
)
from app.db.repositories.videos import get_video
from app.services.errors import ServiceValidationError

logger = get_logger(__name__)
LLMResponder = Callable[
    [str, str, Sequence[Mapping[str, object]] | None],
    tuple[str, list[MemoryMessage]],
]


@dataclass(frozen=True, slots=True)
class ChatAnswer:
    """Assistant answer for a chat turn."""

    answer: str


class ChatService:
    """Coordinate interview practice sessions and LLM calls."""

    def __init__(
        self,
        *,
        app_settings: Settings,
        responder: LLMResponder,
    ) -> None:
        self._settings = app_settings
        self._responder = responder

    def start_chat(self, video_id: int) -> int:
        """Create a chat session for a ready video."""
        video = self._get_ready_video(video_id)

        sessions_total = count_chat_sessions_by_video(video_id)
        if sessions_total >= self._settings.chat_sessions_per_video_limit:
            raise ServiceValidationError(
                "The chat session limit for this video has been reached. "
                "Continue an existing chat or delete an old one.",
                status_code=409,
                details={
                    "sessions_limit": self._settings.chat_sessions_per_video_limit,
                    "sessions_total": sessions_total,
                    "video_id": video_id,
                },
            )

        session_title = _video_title(video)
        session_id = create_chat_session(video_id, session_title)
        logger.info(
            "Chat session created: session_id=%s video_id=%s",
            session_id,
            video_id,
        )
        return session_id

    def send_message(self, session_id: int, message: str) -> ChatAnswer:
        """Send a user message and store the assistant answer."""
        session = get_chat_session(session_id)
        if session is None:
            raise ServiceValidationError("Chat session was not found", status_code=404)

        video_id = _int_field(session, "video_id")
        if video_id is None:
            raise ServiceValidationError(
                "The chat session is not attached to a video",
                status_code=409,
            )

        video = self._get_ready_video(video_id)
        transcript = _text_field(video, "transcript")
        if transcript is None:
            raise ServiceValidationError(
                "The video transcript is not available yet",
                status_code=409,
            )

        memory = get_messages(
            session_id,
            limit=self._settings.llm_memory_messages_limit,
        )
        system_prompt = build_interview_coach_system_prompt(transcript)

        logger.info("Chat message received: session_id=%s", session_id)
        answer, _ = self._responder(system_prompt, message, memory)

        add_message(session_id, "user", message)
        add_message(session_id, "assistant", answer)
        logger.info("Assistant answer stored: session_id=%s", session_id)

        return ChatAnswer(answer=answer)

    def _get_ready_video(self, video_id: int) -> DatabaseRecord:
        """Return a ready video or raise a user-facing service error."""
        video = get_video(video_id)
        if video is None:
            raise ServiceValidationError("Video was not found", status_code=404)

        status = _video_status(video)
        if status != VideoStatus.READY:
            raise ServiceValidationError(
                "The video is not ready for interview practice yet",
                status_code=409,
                details={"video_id": video_id, "status": status.value},
            )

        return video


def get_chat_service() -> ChatService:
    """Build the default chat service."""
    return ChatService(app_settings=settings, responder=ask_llm)


def build_interview_coach_system_prompt(transcript: str) -> str:
    """Build the system prompt for IT interview English practice."""
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
        If needed, add a short native-language clarification, but keep the main
        practice in English.

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
        - If the user writes in another language, answer briefly in that language,
          then suggest an English version to practice.
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


def _video_status(record: DatabaseRecord) -> VideoStatus:
    """Extract a video status from a database record."""
    raw_status = record.get("status")
    if isinstance(raw_status, str):
        try:
            return VideoStatus(raw_status)
        except ValueError:
            logger.warning("Unknown video status in database: %s", raw_status)
    return VideoStatus.QUEUED


def _int_field(record: DatabaseRecord, field_name: str) -> int | None:
    """Extract an integer field from a database record."""
    value = record.get(field_name)
    if isinstance(value, int):
        return value
    return None


def _text_field(record: DatabaseRecord, field_name: str) -> str | None:
    """Extract a non-empty text field from a database record."""
    value = record.get(field_name)
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _video_title(record: DatabaseRecord) -> str | None:
    """Build a chat title from video metadata when available."""
    title = _text_field(record, "title")
    if title is not None:
        return title
    return _text_field(record, "youtube_video_id")
