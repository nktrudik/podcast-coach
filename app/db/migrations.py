import sqlite3

from app.core.errors import ValidationAppError
from app.core.logger import get_logger
from app.core.youtube import normalize_youtube_url
from app.db.connection import get_connection
from app.db.errors import DatabaseOperationError
from app.db.sequences import reset_sequence

logger = get_logger(__name__)


def _get_table_columns(conn: sqlite3.Connection, table_name: str) -> set[str]:
    """Возвращает множество имен колонок таблицы."""
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return {str(row["name"]) for row in rows}


def _merge_video_duplicates(
    conn: sqlite3.Connection,
    *,
    keep_video_id: int,
    duplicate_video_id: int,
) -> None:
    """Переносит ссылки на дублирующееся видео и удаляет дубль."""
    conn.execute(
        "UPDATE chat_sessions SET video_id = ? WHERE video_id = ?",
        (keep_video_id, duplicate_video_id),
    )
    conn.execute("DELETE FROM videos WHERE id = ?", (duplicate_video_id,))


def _normalize_videos_table_data(conn: sqlite3.Connection) -> None:
    """Нормализует URL видео, заполняет youtube_video_id и объединяет дубли."""
    rows = conn.execute(
        """
        SELECT id, youtube_url, youtube_video_id
        FROM videos
        ORDER BY id
        """
    ).fetchall()

    canonical_video_map: dict[str, int] = {}
    merged_count = 0

    for row in rows:
        row_id = int(row["id"])
        row_video_id = row["youtube_video_id"]
        row_url = row["youtube_url"]

        normalized_video_id: str | None = None
        normalized_url: str | None = None

        if isinstance(row_video_id, str) and row_video_id.strip():
            normalized_video_id = row_video_id.strip()
            normalized_url = row_url
        elif isinstance(row_url, str) and row_url.strip():
            try:
                normalized_url, normalized_video_id = normalize_youtube_url(row_url)
                conn.execute(
                    """
                    UPDATE videos
                    SET youtube_url = ?, youtube_video_id = ?
                    WHERE id = ?
                    """,
                    (normalized_url, normalized_video_id, row_id),
                )
            except ValidationAppError:
                logger.warning(
                    "Пропущена запись video_id=%s: не удалось извлечь youtube_video_id из URL",
                    row_id,
                )
                continue

        if normalized_video_id is None:
            continue

        existing_row_id = canonical_video_map.get(normalized_video_id)
        if existing_row_id is None:
            canonical_video_map[normalized_video_id] = row_id
            continue

        if existing_row_id == row_id:
            continue

        _merge_video_duplicates(
            conn,
            keep_video_id=existing_row_id,
            duplicate_video_id=row_id,
        )
        merged_count += 1

    if merged_count > 0:
        reset_sequence(conn, "videos")
        logger.info("Объединены дубли видео при миграции: %s", merged_count)


def _ensure_videos_schema(conn: sqlite3.Connection) -> None:
    """Проводит миграцию таблицы videos к актуальной схеме MVP."""
    columns = _get_table_columns(conn, "videos")
    if "youtube_video_id" not in columns:
        conn.execute("ALTER TABLE videos ADD COLUMN youtube_video_id TEXT")
    if "title" not in columns:
        conn.execute("ALTER TABLE videos ADD COLUMN title TEXT")

    _normalize_videos_table_data(conn)

    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_videos_youtube_video_id
        ON videos (youtube_video_id)
        """
    )


def init_db() -> None:
    """Инициализирует таблицы приложения в базе данных."""
    try:
        with get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS videos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    youtube_url TEXT,
                    youtube_video_id TEXT,
                    title TEXT,
                    transcript TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS chat_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    video_id INTEGER,
                    title TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (video_id) REFERENCES videos (id) ON DELETE SET NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES chat_sessions (id) ON DELETE CASCADE
                )
                """
            )

            _ensure_videos_schema(conn)

            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_chat_sessions_video_id
                ON chat_sessions (video_id)
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_messages_session_id
                ON messages (session_id)
                """
            )
        logger.info("База данных успешно инициализирована")
    except sqlite3.Error as exc:
        raise DatabaseOperationError("Не удалось инициализировать базу данных") from exc
