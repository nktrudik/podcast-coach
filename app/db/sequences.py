from typing import Any

from psycopg import Connection, sql

_SEQUENCE_TABLES = {"videos", "chat_sessions", "messages"}


def reset_sequence(conn: Connection[Any], table_name: str) -> None:
    """Синхронизирует PostgreSQL identity sequence с текущим max id таблицы."""
    if table_name not in _SEQUENCE_TABLES:
        raise ValueError(f"Недопустимая таблица для сброса sequence: {table_name}")

    query = sql.SQL(
        """
        SELECT setval(
            pg_get_serial_sequence(%s, 'id'),
            COALESCE((SELECT MAX(id) FROM {table}), 1),
            (SELECT COUNT(*) FROM {table}) > 0
        )
        """
    ).format(table=sql.Identifier(table_name))

    conn.execute(query, (table_name,))
