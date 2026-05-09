import sqlite3
from typing import Any

from app.core.errors import ValidationAppError
from app.core.logger import get_logger
from app.core.youtube import normalize_youtube_url
from app.db.connection import get_connection
from app.db.errors import DatabaseOperationError, DatabaseValidationError
from app.db.sequences import reset_sequence
from app.db.validation import (
    validate_non_empty_text,
    validate_optional_text,
    validate_positive_int,
    validate_youtube_video_id,
)

logger = get_logger(__name__)


def save_video_transcript(
    transcript: str,
    youtube_url: str,
    youtube_video_id: str,
    title: str | None = None,
) -> int:
    """Сохраняет транскрипт видео и возвращает идентификатор записи."""
    normalized_transcript = validate_non_empty_text(transcript, "transcript")
    normalized_url = validate_non_empty_text(youtube_url, "youtube_url")
    normalized_video_id = validate_youtube_video_id(youtube_video_id)
    normalized_title = validate_optional_text(title, "title")

    try:
        with get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO videos (youtube_url, youtube_video_id, title, transcript)
                VALUES (?, ?, ?, ?)
                """,
                (normalized_url, normalized_video_id, normalized_title, normalized_transcript),
            )
            return int(cursor.lastrowid)
    except sqlite3.IntegrityError:
        video = get_video_by_youtube_video_id(normalized_video_id)
        if video:
            video_id = int(video["id"])
            existing_title = video.get("title")
            has_existing_title = isinstance(existing_title, str) and bool(existing_title.strip())
            if normalized_title and not has_existing_title:
                update_video_title(video_id, normalized_title)
            return video_id
        raise DatabaseOperationError("Не удалось сохранить транскрипт видео")
    except sqlite3.Error as exc:
        raise DatabaseOperationError("Не удалось сохранить транскрипт видео") from exc


def list_videos() -> list[dict[str, Any]]:
    """Возвращает список загруженных видео без полного транскрипта."""
    try:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT id, youtube_url, youtube_video_id, title, created_at
                FROM videos
                ORDER BY id DESC
                """
            ).fetchall()
    except sqlite3.Error as exc:
        raise DatabaseOperationError("Не удалось получить список видео") from exc

    return [dict(row) for row in rows]


def get_video(video_id: int) -> dict[str, Any] | None:
    """Возвращает видео по идентификатору."""
    validated_video_id = validate_positive_int(video_id, "video_id")

    try:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM videos WHERE id = ?",
                (validated_video_id,),
            ).fetchone()
    except sqlite3.Error as exc:
        raise DatabaseOperationError("Не удалось получить видео") from exc

    return dict(row) if row else None


def get_video_by_youtube_video_id(youtube_video_id: str) -> dict[str, Any] | None:
    """Возвращает видео по youtube_video_id."""
    normalized_video_id = validate_youtube_video_id(youtube_video_id)

    try:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM videos WHERE youtube_video_id = ?",
                (normalized_video_id,),
            ).fetchone()
    except sqlite3.Error as exc:
        raise DatabaseOperationError("Не удалось получить видео по youtube_video_id") from exc

    return dict(row) if row else None


def get_video_by_url(youtube_url: str) -> dict[str, Any] | None:
    """Возвращает видео по YouTube URL через нормализацию в youtube_video_id."""
    normalized_url = validate_non_empty_text(youtube_url, "youtube_url")

    try:
        _, youtube_video_id = normalize_youtube_url(normalized_url)
    except ValidationAppError as exc:
        raise DatabaseValidationError("Передана некорректная ссылка YouTube") from exc

    return get_video_by_youtube_video_id(youtube_video_id)


def update_video_title(video_id: int, title: str) -> None:
    """Обновляет title у видео, если поле еще не заполнено."""
    validated_video_id = validate_positive_int(video_id, "video_id")
    normalized_title = validate_non_empty_text(title, "title")

    try:
        with get_connection() as conn:
            conn.execute(
                """
                UPDATE videos
                SET title = ?
                WHERE id = ?
                  AND (title IS NULL OR TRIM(title) = '')
                """,
                (normalized_title, validated_video_id),
            )
    except sqlite3.Error as exc:
        raise DatabaseOperationError("Не удалось обновить title видео") from exc


def count_videos() -> int:
    """Возвращает общее количество загруженных видео."""
    try:
        with get_connection() as conn:
            row = conn.execute(
                """
                SELECT COUNT(*) AS total
                FROM videos
                """
            ).fetchone()
    except sqlite3.Error as exc:
        raise DatabaseOperationError("Не удалось посчитать количество видео") from exc

    total = row["total"] if row else 0
    return int(total) if isinstance(total, int) else 0


def delete_video(video_id: int) -> bool:
    """Удаляет видео по id и возвращает факт удаления."""
    validated_video_id = validate_positive_int(video_id, "video_id")

    try:
        with get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM videos WHERE id = ?",
                (validated_video_id,),
            )
            deleted = cursor.rowcount > 0
            if deleted:
                reset_sequence(conn, "videos")
                logger.info("Видео удалено: video_id=%s", validated_video_id)
            return deleted
    except sqlite3.Error as exc:
        raise DatabaseOperationError("Не удалось удалить видео") from exc
