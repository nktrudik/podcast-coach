import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass

from app.clients.stt import transcribe_audio
from app.clients.youtube import download_audio, get_video_metadata
from app.core.config import Settings, settings
from app.core.errors import AppError
from app.core.logger import get_logger
from app.core.status import VideoStatus
from app.core.types import DatabaseRecord
from app.core.youtube import normalize_youtube_url
from app.db.repositories.videos import (
    count_videos,
    create_video_job,
    get_video,
    get_video_by_youtube_video_id,
    mark_video_failed,
    mark_video_processing,
    mark_video_queued,
    mark_video_ready,
)
from app.services.errors import ServiceValidationError, VideoProcessingError

logger = get_logger(__name__)

MetadataProvider = Callable[[str], Mapping[str, object]]
AudioDownloader = Callable[[str], str]
Transcriber = Callable[[str], str]


@dataclass(frozen=True, slots=True)
class VideoJob:
    """Video processing job returned by the service."""

    video_id: int
    job_id: str
    status: VideoStatus


class VideoProcessingService:
    """Coordinate YouTube ingestion, STT, and video job persistence."""

    def __init__(
        self,
        *,
        app_settings: Settings,
        metadata_provider: MetadataProvider,
        audio_downloader: AudioDownloader,
        transcriber: Transcriber,
    ) -> None:
        self._settings = app_settings
        self._metadata_provider = metadata_provider
        self._audio_downloader = audio_downloader
        self._transcriber = transcriber

    def create_job(self, youtube_url: str) -> VideoJob:
        """Create or reuse a video processing job."""
        normalized_url, youtube_video_id = self._normalize_url(youtube_url)
        existing_video = get_video_by_youtube_video_id(youtube_video_id)
        if existing_video is not None:
            video_id = _record_id(existing_video, "video")
            status = _record_status(existing_video)
            if status == VideoStatus.FAILED:
                mark_video_queued(video_id)
                status = VideoStatus.QUEUED
            return VideoJob(video_id=video_id, job_id=_job_id(video_id), status=status)

        videos_total = count_videos()
        if videos_total >= self._settings.uploaded_videos_limit:
            raise ServiceValidationError(
                "The uploaded video limit has been reached. Delete an existing "
                "video before adding a new one.",
                details={
                    "videos_limit": self._settings.uploaded_videos_limit,
                    "videos_total": videos_total,
                },
            )

        video_id = create_video_job(normalized_url, youtube_video_id)
        return VideoJob(
            video_id=video_id,
            job_id=_job_id(video_id),
            status=VideoStatus.QUEUED,
        )

    def process_job(self, video_id: int) -> None:
        """Process a queued video job and store the final state."""
        video = get_video(video_id)
        if video is None:
            logger.warning("Video job was not found: video_id=%s", video_id)
            return

        status = _record_status(video)
        if status == VideoStatus.READY:
            logger.info("Video job is already ready: video_id=%s", video_id)
            return

        youtube_url = _record_text(video, "youtube_url")
        if youtube_url is None:
            self._safe_mark_failed(video_id, "Video job does not contain a YouTube URL")
            return

        try:
            mark_video_processing(video_id)
            self._process_ready_video(video_id, youtube_url)
        except AppError as exc:
            logger.warning(
                "Video job failed: video_id=%s code=%s details=%s",
                video_id,
                exc.error_code,
                exc.details,
            )
            self._safe_mark_failed(video_id, exc.message)
        except Exception as exc:
            logger.exception(
                "Unexpected video processing failure: video_id=%s",
                video_id,
            )
            self._safe_mark_failed(video_id, "Failed to process the video")
            raise VideoProcessingError("Failed to process the video") from exc
        finally:
            _clear_temp_folder()

    def _process_ready_video(self, video_id: int, youtube_url: str) -> None:
        """Run the actual media processing pipeline for a video."""
        normalized_url, youtube_video_id = self._normalize_url(youtube_url)
        metadata = self._metadata_provider(normalized_url)
        video_title = _optional_text(metadata.get("title"))
        duration_seconds = _duration_seconds(metadata.get("duration_seconds"))
        if duration_seconds is None:
            raise ServiceValidationError(
                "Could not determine the video duration. "
                "Try another link or retry later."
            )

        max_duration_seconds = self._max_video_duration_seconds()
        if duration_seconds > max_duration_seconds:
            raise ServiceValidationError(
                "This video is too long for the current processing limit.",
                details={
                    "max_duration_seconds": max_duration_seconds,
                    "actual_duration_seconds": duration_seconds,
                    "max_duration_minutes": self._settings.max_video_duration_minutes,
                    "actual_duration": _format_duration(duration_seconds),
                },
            )

        audio_path = self._audio_downloader(normalized_url)
        transcript = self._transcriber(audio_path)
        mark_video_ready(
            video_id=video_id,
            transcript=transcript,
            youtube_url=normalized_url,
            youtube_video_id=youtube_video_id,
            title=video_title,
        )
        logger.info("Video job completed successfully: video_id=%s", video_id)

    def _normalize_url(self, youtube_url: str) -> tuple[str, str]:
        """Validate and normalize a YouTube URL."""
        if not isinstance(youtube_url, str):
            raise ServiceValidationError("YouTube URL must be a string")

        normalized_url = youtube_url.strip()
        if not normalized_url:
            raise ServiceValidationError("YouTube URL must not be empty")

        try:
            return normalize_youtube_url(normalized_url)
        except Exception as exc:
            raise ServiceValidationError("Invalid YouTube URL") from exc

    def _max_video_duration_seconds(self) -> int:
        """Return the configured video duration limit in seconds."""
        return int(self._settings.max_video_duration_minutes) * 60

    def _safe_mark_failed(self, video_id: int, error_message: str) -> None:
        """Persist a failed status without hiding the original processing error."""
        try:
            mark_video_failed(video_id, error_message)
        except AppError:
            logger.exception("Failed to persist video failure: video_id=%s", video_id)


def get_video_processing_service() -> VideoProcessingService:
    """Build the default video processing service."""
    return VideoProcessingService(
        app_settings=settings,
        metadata_provider=get_video_metadata,
        audio_downloader=download_audio,
        transcriber=transcribe_audio,
    )


def process_video(youtube_url: str) -> int:
    """Synchronously process a video for backwards-compatible internal callers."""
    service = get_video_processing_service()
    job = service.create_job(youtube_url)
    if job.status != VideoStatus.READY:
        service.process_job(job.video_id)
    return job.video_id


def _clear_temp_folder() -> None:
    """Clear the temporary media directory without interrupting the main flow."""
    temp_dir = os.path.join(".", "temp")

    if not os.path.exists(temp_dir):
        return

    try:
        for filename in os.listdir(temp_dir):
            file_path = os.path.join(temp_dir, filename)
            if os.path.isfile(file_path):
                os.remove(file_path)
    except OSError as exc:
        logger.warning("Failed to fully clear the temporary folder: %s", exc)


def _format_duration(seconds: int) -> str:
    """Format seconds as a compact human-readable duration."""
    minutes, remainder_seconds = divmod(seconds, 60)
    if remainder_seconds == 0:
        return f"{minutes} min"
    return f"{minutes} min {remainder_seconds} sec"


def _record_id(record: DatabaseRecord, entity_name: str) -> int:
    """Extract an integer id from a database record."""
    record_id = record.get("id")
    if not isinstance(record_id, int):
        raise VideoProcessingError(f"The {entity_name} record has an invalid id")
    return record_id


def _record_status(record: DatabaseRecord) -> VideoStatus:
    """Extract a video status from a database record."""
    raw_status = record.get("status")
    if isinstance(raw_status, str):
        try:
            return VideoStatus(raw_status)
        except ValueError:
            logger.warning("Unknown video status in database: %s", raw_status)
    return VideoStatus.QUEUED


def _record_text(record: DatabaseRecord, field_name: str) -> str | None:
    """Extract a non-empty string field from a database record."""
    value = record.get(field_name)
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _optional_text(value: object) -> str | None:
    """Return a stripped string or None."""
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _duration_seconds(value: object) -> int | None:
    """Return a positive integer duration or None."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int) and value > 0:
        return value
    return None


def _job_id(video_id: int) -> str:
    """Build a stable public job id for a video job."""
    return f"video-{video_id}"
