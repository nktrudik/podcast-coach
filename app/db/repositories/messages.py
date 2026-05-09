import sqlite3
from typing import Any

from app.db.connection import get_connection
from app.db.errors import DatabaseOperationError, DatabaseValidationError
from app.db.validation import (
    validate_messages_limit,
    validate_non_empty_text,
    validate_positive_int,
)

_ALLOWED_ROLES = {"user", "assistant", "system"}


def add_message(
    session_id: int,
    role: str,
    content: str,
) -> int:
    """Сохраняет сообщение в чате и возвращает его идентификатор."""
    validated_session_id = validate_positive_int(session_id, "session_id")
    normalized_role = validate_non_empty_text(role, "role")
    normalized_content = validate_non_empty_text(content, "content")

    if normalized_role not in _ALLOWED_ROLES:
        raise DatabaseValidationError("Роль сообщения должна быть user, assistant или system")

    try:
        with get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO messages (session_id, role, content)
                VALUES (?, ?, ?)
                """,
                (validated_session_id, normalized_role, normalized_content),
            )
            return int(cursor.lastrowid)
    except sqlite3.Error as exc:
        raise DatabaseOperationError("Не удалось сохранить сообщение") from exc


def get_messages(session_id: int, limit: int | None = None) -> list[dict[str, Any]]:
    """Возвращает историю сообщений для указанной чат-сессии."""
    validated_session_id = validate_positive_int(session_id, "session_id")
    validated_limit = validate_messages_limit(limit)

    try:
        with get_connection() as conn:
            if validated_limit is None:
                rows = conn.execute(
                    """
                    SELECT id, role, content, created_at
                    FROM messages
                    WHERE session_id = ?
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
                        WHERE session_id = ?
                        ORDER BY id DESC
                        LIMIT ?
                    )
                    ORDER BY id
                    """,
                    (validated_session_id, validated_limit),
                ).fetchall()
    except sqlite3.Error as exc:
        raise DatabaseOperationError("Не удалось получить историю сообщений") from exc

    return [dict(row) for row in rows]
