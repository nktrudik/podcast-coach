import os
import sqlite3

from app.core.config import settings
from app.db.errors import DatabaseOperationError


def get_connection() -> sqlite3.Connection:
    """Creates a SQLite connection with foreign keys enabled."""
    try:
        os.makedirs(os.path.dirname(settings.db_path), exist_ok=True)
        conn = sqlite3.connect(settings.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn
    except Exception as exc:
        raise DatabaseOperationError("Не удалось подключиться к базе данных") from exc
