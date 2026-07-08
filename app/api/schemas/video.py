from pydantic import BaseModel, Field, field_validator

from app.core.status import VideoStatus
from app.core.youtube import normalize_youtube_url


class UploadVideoRequest(BaseModel):
    """Request body for creating a YouTube video processing job."""

    youtube_url: str = Field(
        min_length=5,
        examples=["https://www.youtube.com/watch?v=gO1Cm_A_pO8"],
    )

    @field_validator("youtube_url")
    @classmethod
    def validate_youtube_url(cls, value: str) -> str:
        """Validate and normalize a YouTube URL."""
        normalized_value = value.strip()
        if not normalized_value:
            raise ValueError("Field youtube_url must not be empty")

        try:
            canonical_url, _ = normalize_youtube_url(normalized_value)
        except Exception as exc:
            raise ValueError("Only valid YouTube URLs are supported") from exc

        return canonical_url


class UploadVideoResponse(BaseModel):
    """Response returned after a processing job is created."""

    job_id: str = Field(examples=["video-42"])
    video_id: int = Field(examples=[42])
    status: VideoStatus = Field(examples=[VideoStatus.QUEUED])


class VideoListItem(BaseModel):
    """Uploaded video item for navigation and polling."""

    id: int
    youtube_url: str | None = None
    youtube_video_id: str | None = None
    title: str | None = None
    status: VideoStatus = VideoStatus.QUEUED
    error_message: str | None = None
    created_at: str
    updated_at: str | None = None


class VideoDetailResponse(BaseModel):
    """Full video state for the detail screen."""

    id: int
    youtube_url: str | None = None
    youtube_video_id: str | None = None
    title: str | None = None
    transcript: str | None = None
    status: VideoStatus = VideoStatus.QUEUED
    error_message: str | None = None
    created_at: str
    updated_at: str | None = None
