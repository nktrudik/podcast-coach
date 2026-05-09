import sqlite3

from app.db.errors import DatabaseValidationError

_ALLOWED_SEQUENCE_TABLES = {"videos", "chat_sessions", "messages"}


def reset_sequence(conn: sqlite3.Connection, table_name: str) -> None:
    """Сбрасывает sqlite_sequence до актуального max id в таблице."""
    if table_name not in _ALLOWED_SEQUENCE_TABLES:
        raise DatabaseValidationError("Передано недопустимое имя таблицы для sequence")

    conn.execute(
        f"""
        UPDATE sqlite_sequence
        SET seq = COALESCE((SELECT MAX(id) FROM {table_name}), 0)
        WHERE name = ?
        """,
        (table_name,),
    )
