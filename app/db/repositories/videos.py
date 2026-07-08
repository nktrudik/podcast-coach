from app.core.errors import ValidationAppError
from app.core.logger import get_logger
from app.core.status import VideoStatus
from app.core.types import DatabaseRecord
from app.core.youtube import normalize_youtube_url
from app.db.connection import get_connection
from app.db.errors import DatabaseOperationError, DatabaseValidationError
from app.db.rows import required_int, to_database_record
from app.db.sequences import reset_sequence
from app.db.validation import (
    validate_non_empty_text,
    validate_optional_text,
    validate_positive_int,
    validate_youtube_video_id,
)
from psycopg import Error, IntegrityError

logger = get_logger(__name__)


def create_video_job(
    youtube_url: str,
    youtube_video_id: str,
    status: VideoStatus = VideoStatus.QUEUED,
) -> int:
    """Create a video processing job and return the video id."""
    normalized_url = validate_non_empty_text(youtube_url, "youtube_url")
    normalized_video_id = validate_youtube_video_id(youtube_video_id)

    try:
        with get_connection() as conn:
            row = conn.execute(
                """
                INSERT INTO videos (
                    youtube_url,
                    youtube_video_id,
                    title,
                    transcript,
                    status,
                    error_message,
                    updated_at
                )
                VALUES (%s, %s, NULL, NULL, %s, NULL, CURRENT_TIMESTAMP::text)
                RETURNING id
                """,
                (normalized_url, normalized_video_id, status.value),
            ).fetchone()
            if row is None:
                raise DatabaseOperationError("The database did not return a video id")
            return required_int(row, "id", "video")
    except IntegrityError:
        existing_video = get_video_by_youtube_video_id(normalized_video_id)
        if existing_video is None:
            raise DatabaseOperationError(
                "Failed to resolve duplicate video job"
            ) from None
        return _record_id(existing_video, "video")
    except Error as exc:
        raise DatabaseOperationError("Failed to create the video job") from exc


def save_video_transcript(
    transcript: str,
    youtube_url: str,
    youtube_video_id: str,
    title: str | None = None,
) -> int:
    """Save a ready transcript and return the video id."""
    normalized_transcript = validate_non_empty_text(transcript, "transcript")
    normalized_url = validate_non_empty_text(youtube_url, "youtube_url")
    normalized_video_id = validate_youtube_video_id(youtube_video_id)
    normalized_title = validate_optional_text(title, "title")

    try:
        with get_connection() as conn:
            row = conn.execute(
                """
                INSERT INTO videos (
                    youtube_url,
                    youtube_video_id,
                    title,
                    transcript,
                    status,
                    error_message,
                    updated_at
                )
                VALUES (%s, %s, %s, %s, %s, NULL, CURRENT_TIMESTAMP::text)
                RETURNING id
                """,
                (
                    normalized_url,
                    normalized_video_id,
                    normalized_title,
                    normalized_transcript,
                    VideoStatus.READY.value,
                ),
            ).fetchone()
            if row is None:
                raise DatabaseOperationError("The database did not return a video id")
            return required_int(row, "id", "video")
    except IntegrityError:
        video = get_video_by_youtube_video_id(normalized_video_id)
        if video:
            video_id = _record_id(video, "video")
            mark_video_ready(
                video_id=video_id,
                transcript=normalized_transcript,
                youtube_url=normalized_url,
                youtube_video_id=normalized_video_id,
                title=normalized_title,
            )
            return video_id
        raise DatabaseOperationError("Failed to save the video transcript") from None
    except Error as exc:
        raise DatabaseOperationError("Failed to save the video transcript") from exc


def mark_video_processing(video_id: int) -> None:
    """Mark a video job as processing."""
    _update_video_status(video_id, VideoStatus.PROCESSING, None)


def mark_video_failed(video_id: int, error_message: str) -> None:
    """Mark a video job as failed with a safe user-facing message."""
    normalized_error = validate_non_empty_text(error_message, "error_message")
    _update_video_status(video_id, VideoStatus.FAILED, normalized_error)


def mark_video_queued(video_id: int) -> None:
    """Reset a failed video job to queued."""
    _update_video_status(video_id, VideoStatus.QUEUED, None)


def mark_video_ready(
    *,
    video_id: int,
    transcript: str,
    youtube_url: str,
    youtube_video_id: str,
    title: str | None,
) -> None:
    """Persist the completed processing result for a video job."""
    validated_video_id = validate_positive_int(video_id, "video_id")
    normalized_transcript = validate_non_empty_text(transcript, "transcript")
    normalized_url = validate_non_empty_text(youtube_url, "youtube_url")
    normalized_video_id = validate_youtube_video_id(youtube_video_id)
    normalized_title = validate_optional_text(title, "title")

    try:
        with get_connection() as conn:
            conn.execute(
                """
                UPDATE videos
                SET transcript = %s,
                    youtube_url = %s,
                    youtube_video_id = %s,
                    title = COALESCE(%s, title),
                    status = %s,
                    error_message = NULL,
                    updated_at = CURRENT_TIMESTAMP::text
                WHERE id = %s
                """,
                (
                    normalized_transcript,
                    normalized_url,
                    normalized_video_id,
                    normalized_title,
                    VideoStatus.READY.value,
                    validated_video_id,
                ),
            )
    except Error as exc:
        raise DatabaseOperationError("Failed to mark the video as ready") from exc


def list_videos() -> list[DatabaseRecord]:
    """Return uploaded videos without the full transcript."""
    try:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT
                    id,
                    youtube_url,
                    youtube_video_id,
                    title,
                    status,
                    error_message,
                    created_at,
                    updated_at
                FROM videos
                ORDER BY id DESC
                """
            ).fetchall()
    except Error as exc:
        raise DatabaseOperationError("Failed to fetch videos") from exc

    return [to_database_record(row) for row in rows]


def get_video(video_id: int) -> DatabaseRecord | None:
    """Return a video by id."""
    validated_video_id = validate_positive_int(video_id, "video_id")

    try:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM videos WHERE id = %s",
                (validated_video_id,),
            ).fetchone()
    except Error as exc:
        raise DatabaseOperationError("Failed to fetch the video") from exc

    return to_database_record(row) if row else None


def get_video_by_youtube_video_id(youtube_video_id: str) -> DatabaseRecord | None:
    """Return a video by YouTube video id."""
    normalized_video_id = validate_youtube_video_id(youtube_video_id)

    try:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM videos WHERE youtube_video_id = %s",
                (normalized_video_id,),
            ).fetchone()
    except Error as exc:
        raise DatabaseOperationError("Failed to fetch the video by YouTube id") from exc

    return to_database_record(row) if row else None


def get_video_by_url(youtube_url: str) -> DatabaseRecord | None:
    """Return a video by YouTube URL after normalizing it to a video id."""
    normalized_url = validate_non_empty_text(youtube_url, "youtube_url")

    try:
        _, youtube_video_id = normalize_youtube_url(normalized_url)
    except ValidationAppError as exc:
        raise DatabaseValidationError("Invalid YouTube URL") from exc

    return get_video_by_youtube_video_id(youtube_video_id)


def update_video_title(video_id: int, title: str) -> None:
    """Update a video title only when the current title is empty."""
    validated_video_id = validate_positive_int(video_id, "video_id")
    normalized_title = validate_non_empty_text(title, "title")

    try:
        with get_connection() as conn:
            conn.execute(
                """
                UPDATE videos
                SET title = %s,
                    updated_at = CURRENT_TIMESTAMP::text
                WHERE id = %s
                  AND (title IS NULL OR TRIM(title) = '')
                """,
                (normalized_title, validated_video_id),
            )
    except Error as exc:
        raise DatabaseOperationError("Failed to update the video title") from exc


def count_videos() -> int:
    """Return the number of uploaded videos."""
    try:
        with get_connection() as conn:
            row = conn.execute(
                """
                SELECT COUNT(*) AS total
                FROM videos
                """
            ).fetchone()
    except Error as exc:
        raise DatabaseOperationError("Failed to count videos") from exc

    total = row["total"] if row else 0
    return int(total) if isinstance(total, int) else 0


def delete_video(video_id: int) -> bool:
    """Delete a video by id and return whether it was removed."""
    validated_video_id = validate_positive_int(video_id, "video_id")

    try:
        with get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM videos WHERE id = %s",
                (validated_video_id,),
            )
            deleted = cursor.rowcount > 0
            if deleted:
                reset_sequence(conn, "videos")
                logger.info("Video deleted: video_id=%s", validated_video_id)
            return deleted
    except Error as exc:
        raise DatabaseOperationError("Failed to delete the video") from exc


def _update_video_status(
    video_id: int,
    status: VideoStatus,
    error_message: str | None,
) -> None:
    """Update only the processing state for a video."""
    validated_video_id = validate_positive_int(video_id, "video_id")

    try:
        with get_connection() as conn:
            conn.execute(
                """
                UPDATE videos
                SET status = %s,
                    error_message = %s,
                    updated_at = CURRENT_TIMESTAMP::text
                WHERE id = %s
                """,
                (status.value, error_message, validated_video_id),
            )
    except Error as exc:
        raise DatabaseOperationError("Failed to update the video status") from exc


def _record_id(record: DatabaseRecord, entity_name: str) -> int:
    """Extract an integer id from a database record."""
    record_id = record.get("id")
    if not isinstance(record_id, int):
        raise DatabaseOperationError(f"The {entity_name} record has an invalid id")
    return record_id
