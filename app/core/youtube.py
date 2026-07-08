from yt_dlp.extractor.youtube import YoutubeIE

from app.core.errors import ValidationAppError


def extract_youtube_video_id(youtube_url: str) -> str:
    """Extract a YouTube video id with the yt-dlp extractor."""
    if not isinstance(youtube_url, str):
        raise ValidationAppError("YouTube URL must be a string")

    normalized_url = youtube_url.strip()
    if not normalized_url:
        raise ValidationAppError("YouTube URL must not be empty")

    try:
        video_id = YoutubeIE.extract_id(normalized_url)
    except Exception as exc:
        raise ValidationAppError(
            "Failed to extract a YouTube video id from the URL",
            details={"youtube_url": normalized_url},
        ) from exc

    if not isinstance(video_id, str) or not video_id.strip():
        raise ValidationAppError(
            "The URL did not contain a valid YouTube video id",
            details={"youtube_url": normalized_url},
        )

    return video_id.strip()


def normalize_youtube_url(youtube_url: str) -> tuple[str, str]:
    """Normalize a YouTube URL and return the canonical URL plus video id."""
    video_id = extract_youtube_video_id(youtube_url)
    return f"https://www.youtube.com/watch?v={video_id}", video_id
