from psycopg import Connection, connect
from psycopg.rows import dict_row

from app.core.config import settings
from app.db.errors import DatabaseOperationError


def _database_url() -> str:
    """Return a PostgreSQL connection URL compatible with psycopg."""
    database_url = settings.database_url.strip()
    if database_url.startswith("postgres://"):
        return f"postgresql://{database_url.removeprefix('postgres://')}"
    return database_url


def get_connection() -> Connection[dict[str, object]]:
    """Create a PostgreSQL connection returning rows as dictionaries."""
    try:
        return connect(_database_url(), row_factory=dict_row)
    except Exception as exc:
        raise DatabaseOperationError("Failed to connect to the database") from exc
