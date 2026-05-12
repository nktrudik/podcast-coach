from psycopg import Connection

_SEQUENCE_TABLES = {"videos", "chat_sessions", "messages"}


def reset_sequence(conn: Connection, table_name: str) -> None:
    """Синхронизирует PostgreSQL identity sequence с текущим max id таблицы."""
    if table_name not in _SEQUENCE_TABLES:
        raise ValueError(f"Недопустимая таблица для сброса sequence: {table_name}")

    conn.execute(
        f"""
        SELECT setval(
            pg_get_serial_sequence(%s, 'id'),
            COALESCE((SELECT MAX(id) FROM {table_name}), 1),
            (SELECT COUNT(*) FROM {table_name}) > 0
        )
        """,
        (table_name,),
    )
