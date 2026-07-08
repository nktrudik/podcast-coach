from psycopg import Connection, sql

_SEQUENCE_TABLES = {"videos", "chat_sessions", "messages"}


def reset_sequence(conn: Connection[dict[str, object]], table_name: str) -> None:
    """Synchronize a PostgreSQL identity sequence with the table max id."""
    if table_name not in _SEQUENCE_TABLES:
        raise ValueError(f"Unsupported table for sequence reset: {table_name}")

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
