from app.core.types import DatabaseRecord
from app.db.connection import get_connection
from app.db.errors import DatabaseOperationError, DatabaseValidationError
from app.db.rows import required_int, to_database_record
from app.db.validation import (
    validate_messages_limit,
    validate_non_empty_text,
    validate_positive_int,
)
from psycopg import Error

_ALLOWED_ROLES = {"user", "assistant", "system"}


def add_message(
    session_id: int,
    role: str,
    content: str,
) -> int:
    """Store a chat message and return its id."""
    validated_session_id = validate_positive_int(session_id, "session_id")
    normalized_role = validate_non_empty_text(role, "role")
    normalized_content = validate_non_empty_text(content, "content")

    if normalized_role not in _ALLOWED_ROLES:
        raise DatabaseValidationError("Message role must be user, assistant, or system")

    try:
        with get_connection() as conn:
            row = conn.execute(
                """
                INSERT INTO messages (session_id, role, content)
                VALUES (%s, %s, %s)
                RETURNING id
                """,
                (validated_session_id, normalized_role, normalized_content),
            ).fetchone()
            if row is None:
                raise DatabaseOperationError("The database did not return a message id")
            return required_int(row, "id", "message")
    except Error as exc:
        raise DatabaseOperationError("Failed to store the message") from exc


def get_messages(session_id: int, limit: int | None = None) -> list[DatabaseRecord]:
    """Return message history for a chat session."""
    validated_session_id = validate_positive_int(session_id, "session_id")
    validated_limit = validate_messages_limit(limit)

    try:
        with get_connection() as conn:
            if validated_limit is None:
                rows = conn.execute(
                    """
                    SELECT id, role, content, created_at
                    FROM messages
                    WHERE session_id = %s
                    ORDER BY id
                    """,
                    (validated_session_id,),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT id, role, content, created_at
                    FROM (
                        SELECT id, role, content, created_at
                        FROM messages
                        WHERE session_id = %s
                        ORDER BY id DESC
                        LIMIT %s
                    )
                    ORDER BY id
                    """,
                    (validated_session_id, validated_limit),
                ).fetchall()
    except Error as exc:
        raise DatabaseOperationError("Failed to fetch message history") from exc

    return [to_database_record(row) for row in rows]
