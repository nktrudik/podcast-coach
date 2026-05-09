from pydantic import BaseModel, Field, field_validator

from app.core.youtube import normalize_youtube_url


class UploadVideoRequest(BaseModel):
    """Запрос на загрузку YouTube-видео для обработки."""

    youtube_url: str = Field(min_length=5)

    @field_validator("youtube_url")
    @classmethod
    def validate_youtube_url(cls, value: str) -> str:
        """Проверяет, что передана валидная непустая ссылка YouTube."""
        normalized_value = value.strip()
        if not normalized_value:
            raise ValueError("Поле youtube_url не должно быть пустым")

        try:
            canonical_url, _ = normalize_youtube_url(normalized_value)
        except Exception as exc:
            raise ValueError("Поддерживаются только корректные ссылки YouTube") from exc

        return canonical_url


class UploadVideoResponse(BaseModel):
    """Ответ после успешной обработки видео."""

    video_id: int


class VideoListItem(BaseModel):
    """Элемент списка загруженных видео."""

    id: int
    youtube_url: str | None = None
    youtube_video_id: str | None = None
    title: str | None = None
    created_at: str


class VideoDetailResponse(BaseModel):
    """Полная информация по видео для экрана деталей."""

    id: int
    youtube_url: str | None = None
    youtube_video_id: str | None = None
    title: str | None = None
    transcript: str
    created_at: str
