import os

from app.clients.youtube import download_audio, get_video_metadata
from app.clients.stt import transcribe_audio
from app.core.config import settings
from app.core.errors import AppError
from app.core.logger import get_logger
from app.core.youtube import normalize_youtube_url
from app.db.repositories.videos import (
    count_videos,
    get_video_by_youtube_video_id,
    save_video_transcript,
)
from app.services.errors import ServiceValidationError, VideoProcessingError

logger = get_logger(__name__)


def _max_video_duration_seconds() -> int:
    """Возвращает лимит длительности ролика в секундах из конфигурации."""
    return int(settings.max_video_duration_minutes) * 60


def _validate_youtube_url(youtube_url: str) -> str:
    """Проверяет входную ссылку на видео."""
    if not isinstance(youtube_url, str):
        raise ServiceValidationError("Ссылка на YouTube должна быть строкой")

    normalized_url = youtube_url.strip()
    if not normalized_url:
        raise ServiceValidationError("Ссылка на YouTube не должна быть пустой")

    return normalized_url


def _clear_temp_folder() -> None:
    """Очищает временную директорию, не прерывая основной процесс при ошибке."""
    temp_dir = os.path.join(".", "temp")

    if not os.path.exists(temp_dir):
        return

    try:
        for filename in os.listdir(temp_dir):
            file_path = os.path.join(temp_dir, filename)
            if os.path.isfile(file_path):
                os.remove(file_path)
    except OSError as exc:
        logger.warning("Не удалось полностью очистить временную папку: %s", exc)


def _format_duration(seconds: int) -> str:
    """Преобразует длительность в секундах в человекочитаемый формат."""
    minutes, remainder_seconds = divmod(seconds, 60)
    if remainder_seconds == 0:
        return f"{minutes} мин"
    return f"{minutes} мин {remainder_seconds} сек"


def process_video(youtube_url: str) -> int:
    """Полностью обрабатывает YouTube-видео и возвращает id записи в БД."""
    raw_url = _validate_youtube_url(youtube_url)

    try:
        normalized_url, youtube_video_id = normalize_youtube_url(raw_url)
    except Exception as exc:
        raise ServiceValidationError("Передана некорректная ссылка YouTube") from exc

    logger.info("Запущена обработка видео")

    try:
        video = get_video_by_youtube_video_id(youtube_video_id)
        if video:
            video_id = int(video["id"])
            logger.info("Видео найдено в кэше БД")
            return video_id

        metadata = get_video_metadata(normalized_url)
        video_title_raw = metadata.get("title")
        video_title = video_title_raw if isinstance(video_title_raw, str) and video_title_raw.strip() else None

        duration_seconds_raw = metadata.get("duration_seconds")
        duration_seconds = duration_seconds_raw if isinstance(duration_seconds_raw, int) else None
        if duration_seconds is None:
            raise ServiceValidationError(
                "Не удалось определить длительность ролика. Попробуй другую ссылку или повтори позже.",
            )

        max_duration_seconds = _max_video_duration_seconds()
        if duration_seconds > max_duration_seconds:
            raise ServiceValidationError(
                f"Этот ролик слишком длинный. Сейчас поддерживаются видео до {settings.max_video_duration_minutes} минут. "
                f"Текущая длительность: {_format_duration(duration_seconds)}.",
                details={
                    "max_duration_seconds": max_duration_seconds,
                    "actual_duration_seconds": duration_seconds,
                },
            )

        videos_total = count_videos()
        if videos_total >= settings.uploaded_videos_limit:
            raise ServiceValidationError(
                f"Достигнут лимит загруженных видео: {settings.uploaded_videos_limit}. "
                "Удали одно из текущих видео, чтобы загрузить новое.",
                details={
                    "videos_limit": settings.uploaded_videos_limit,
                    "videos_total": videos_total,
                },
            )

        audio_path = download_audio(normalized_url)
        transcript = transcribe_audio(audio_path)
        video_id = save_video_transcript(
            transcript=transcript,
            youtube_url=normalized_url,
            youtube_video_id=youtube_video_id,
            title=video_title,
        )

        if video_id <= 0:
            raise VideoProcessingError("Получен некорректный идентификатор видео после сохранения")

        logger.info("Видео успешно обработано и сохранено")
        return video_id
    except AppError:
        raise
    except Exception as exc:
        logger.exception("Критическая ошибка обработки видео")
        raise VideoProcessingError("Не удалось обработать видео") from exc
    finally:
        _clear_temp_folder()
