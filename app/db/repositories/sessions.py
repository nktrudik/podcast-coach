from typing import Any

from psycopg import Error

from app.core.logger import get_logger
from app.db.connection import get_connection
from app.db.errors import DatabaseOperationError
from app.db.sequences import reset_sequence
from app.db.validation import validate_optional_text, validate_positive_int

logger = get_logger(__name__)


def count_chat_sessions_by_video(video_id: int) -> int:
    """Возвращает количество чат-сессий, привязанных к видео."""
    validated_video_id = validate_positive_int(video_id, "video_id")

    try:
        with get_connection() as conn:
            row = conn.execute(
                """
                SELECT COUNT(*) AS total
                FROM chat_sessions
                WHERE video_id = %s
                """,
                (validated_video_id,),
            ).fetchone()
    except Error as exc:
        raise DatabaseOperationError(
            "Не удалось посчитать чат-сессии по видео"
        ) from exc

    total = row["total"] if row else 0
    return int(total) if isinstance(total, int) else 0


def create_chat_session(video_id: int | None = None, title: str | None = None) -> int:
    """Создает чат-сессию и возвращает ее идентификатор."""
    normalized_video_id = (
        None if video_id is None else validate_positive_int(video_id, "video_id")
    )
    normalized_title = validate_optional_text(title, "title")

    try:
        with get_connection() as conn:
            row = conn.execute(
                """
                INSERT INTO chat_sessions (video_id, title)
                VALUES (%s, %s)
                RETURNING id
                """,
                (normalized_video_id, normalized_title),
            ).fetchone()
            if row is None:
                raise DatabaseOperationError("База данных не вернула id чат-сессии")
            return int(row["id"])
    except Error as exc:
        raise DatabaseOperationError("Не удалось создать чат-сессию") from exc


def get_chat_session(session_id: int) -> dict[str, Any] | None:
    """Возвращает чат-сессию по идентификатору."""
    validated_session_id = validate_positive_int(session_id, "session_id")

    try:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM chat_sessions WHERE id = %s",
                (validated_session_id,),
            ).fetchone()
    except Error as exc:
        raise DatabaseOperationError("Не удалось получить чат-сессию") from exc

    return dict(row) if row else None


def delete_chat_session(session_id: int) -> bool:
    """Удаляет чат-сессию и синхронизирует sequence таблиц."""
    validated_session_id = validate_positive_int(session_id, "session_id")

    try:
        with get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM chat_sessions WHERE id = %s",
                (validated_session_id,),
            )
            deleted = cursor.rowcount > 0
            if deleted:
                reset_sequence(conn, "chat_sessions")
                reset_sequence(conn, "messages")
                logger.info("Чат-сессия удалена: session_id=%s", validated_session_id)
            return deleted
    except Error as exc:
        raise DatabaseOperationError("Не удалось удалить чат-сессию") from exc


def list_chat_sessions() -> list[dict[str, Any]]:
    """Возвращает список чат-сессий в обратном порядке создания."""
    try:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM chat_sessions
                ORDER BY id DESC
                """
            ).fetchall()
    except Error as exc:
        raise DatabaseOperationError("Не удалось получить список чат-сессий") from exc

    return [dict(row) for row in rows]
