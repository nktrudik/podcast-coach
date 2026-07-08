from app.core.logger import get_logger
from app.core.types import DatabaseRecord
from app.db.connection import get_connection
from app.db.errors import DatabaseOperationError
from app.db.rows import required_int, to_database_record
from app.db.sequences import reset_sequence
from app.db.validation import validate_optional_text, validate_positive_int
from psycopg import Error

logger = get_logger(__name__)


def count_chat_sessions_by_video(video_id: int) -> int:
    """Return the number of chat sessions attached to a video."""
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
        raise DatabaseOperationError("Failed to count chat sessions") from exc

    total = row["total"] if row else 0
    return int(total) if isinstance(total, int) else 0


def create_chat_session(video_id: int | None = None, title: str | None = None) -> int:
    """Create a chat session and return its id."""
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
                raise DatabaseOperationError(
                    "The database did not return a chat session id"
                )
            return required_int(row, "id", "chat session")
    except Error as exc:
        raise DatabaseOperationError("Failed to create the chat session") from exc


def get_chat_session(session_id: int) -> DatabaseRecord | None:
    """Return a chat session by id."""
    validated_session_id = validate_positive_int(session_id, "session_id")

    try:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM chat_sessions WHERE id = %s",
                (validated_session_id,),
            ).fetchone()
    except Error as exc:
        raise DatabaseOperationError("Failed to fetch the chat session") from exc

    return to_database_record(row) if row else None


def delete_chat_session(session_id: int) -> bool:
    """Delete a chat session and synchronize related identity sequences."""
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
                logger.info("Chat session deleted: session_id=%s", validated_session_id)
            return deleted
    except Error as exc:
        raise DatabaseOperationError("Failed to delete the chat session") from exc


def list_chat_sessions() -> list[DatabaseRecord]:
    """Return chat sessions in reverse creation order."""
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
        raise DatabaseOperationError("Failed to fetch chat sessions") from exc

    return [to_database_record(row) for row in rows]
