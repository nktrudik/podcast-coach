from yt_dlp.extractor.youtube import YoutubeIE

from app.core.errors import ValidationAppError


def extract_youtube_video_id(youtube_url: str) -> str:
    """Извлекает youtube_video_id из URL через готовый extractor yt-dlp."""
    if not isinstance(youtube_url, str):
        raise ValidationAppError("Ссылка на YouTube должна быть строкой")

    normalized_url = youtube_url.strip()
    if not normalized_url:
        raise ValidationAppError("Ссылка на YouTube не должна быть пустой")

    try:
        video_id = YoutubeIE.extract_id(normalized_url)
    except Exception as exc:
        raise ValidationAppError(
            "Не удалось извлечь youtube_video_id из ссылки",
            details={"youtube_url": normalized_url},
        ) from exc

    if not isinstance(video_id, str) or not video_id.strip():
        raise ValidationAppError(
            "Из ссылки не удалось получить youtube_video_id",
            details={"youtube_url": normalized_url},
        )

    return video_id.strip()


def normalize_youtube_url(youtube_url: str) -> tuple[str, str]:
    """Нормализует YouTube URL в канонический формат и возвращает URL + video_id."""
    video_id = extract_youtube_video_id(youtube_url)
    return f"https://www.youtube.com/watch?v={video_id}", video_id
