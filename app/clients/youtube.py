import os
import subprocess
import time
from typing import Any

import yt_dlp
from yt_dlp.utils import DownloadError

from app.clients.errors import ClientValidationError, YouTubeDownloadError
from app.core.config import settings
from app.core.logger import get_logger
from app.core.youtube import normalize_youtube_url

logger = get_logger(__name__)


def _run_youtube_with_retry(operation_name: str, operation):
    """Выполняет YouTube-операцию с мягкими повторами для временных ошибок."""
    last_exc: YouTubeDownloadError | None = None
    for attempt in range(1, settings.youtube_max_retries + 1):
        try:
            return operation()
        except YouTubeDownloadError as exc:
            last_exc = exc
            retryable = exc.details.get("retryable", True)
            if not retryable or attempt >= settings.youtube_max_retries:
                raise

            logger.warning(
                "%s: временная ошибка на попытке %s/%s",
                operation_name,
                attempt,
                settings.youtube_max_retries,
            )
            if settings.youtube_retry_delay_seconds > 0:
                time.sleep(settings.youtube_retry_delay_seconds)

    if last_exc is not None:
        raise last_exc

    raise RuntimeError("Некорректное состояние повторных попыток YouTube")


def _create_temp_folder() -> str:
    """Создает папку для временных файлов и возвращает ее путь."""
    temp_dir = os.path.join(".", "temp")
    os.makedirs(temp_dir, exist_ok=True)
    return temp_dir


def _clear_temp_folder() -> None:
    """Очищает временные файлы перед новой попыткой скачивания."""
    temp_dir = _create_temp_folder()
    for filename in os.listdir(temp_dir):
        file_path = os.path.join(temp_dir, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.remove(file_path)
        except OSError as exc:
            logger.warning("Не удалось удалить временный файл перед retry: %s", exc)


def _is_non_retryable_download_error(exc: DownloadError) -> bool:
    """Определяет ошибки YouTube, которые нет смысла повторять подряд."""
    message = str(exc).lower()
    non_retryable_markers = (
        "403",
        "429",
        "forbidden",
        "too many requests",
        "sign in to confirm",
        "confirm you're not a bot",
        "confirm you’re not a bot",
        "not a bot",
    )
    return any(marker in message for marker in non_retryable_markers)


def _build_ydl_options(**base_options: Any) -> dict[str, Any]:
    """Собирает yt-dlp options и безопасно подключает cookies, если они заданы."""
    ydl_opts = dict(base_options)
    cookies_file = settings.youtube_cookies_file.strip() if settings.youtube_cookies_file else ""
    cookies_enabled = bool(cookies_file)
    logger.info("YouTube cookies enabled: %s", cookies_enabled)

    if not cookies_enabled:
        return ydl_opts

    if not os.path.isfile(cookies_file):
        raise YouTubeDownloadError(
            "Файл YouTube cookies не найден",
            details={"cookies_configured": True, "retryable": False},
        )

    ydl_opts["cookiefile"] = cookies_file
    return ydl_opts


def _validate_youtube_url(youtube_url: str) -> str:
    """Проверяет, что передана непустая ссылка YouTube."""
    if not isinstance(youtube_url, str):
        raise ClientValidationError("Ссылка на YouTube должна быть строкой")

    normalized_url = youtube_url.strip()
    if not normalized_url:
        raise ClientValidationError("Ссылка на YouTube не должна быть пустой")

    try:
        canonical_url, _ = normalize_youtube_url(normalized_url)
    except Exception as exc:
        raise ClientValidationError("Поддерживаются только корректные ссылки YouTube") from exc

    return canonical_url


def _extract_duration_seconds(raw_value: Any) -> int | None:
    """Извлекает длительность в секундах из метаданных yt-dlp."""
    if isinstance(raw_value, bool):
        return None

    if isinstance(raw_value, int):
        return raw_value if raw_value > 0 else None

    if isinstance(raw_value, float):
        parsed = int(raw_value)
        return parsed if parsed > 0 else None

    if isinstance(raw_value, str):
        normalized = raw_value.strip()
        if normalized.isdigit():
            parsed = int(normalized)
            return parsed if parsed > 0 else None

    return None


def get_video_metadata(youtube_url: str) -> dict[str, Any]:
    """Возвращает метаданные YouTube-видео: title и duration_seconds."""
    normalized_url = _validate_youtube_url(youtube_url)

    ydl_opts = _build_ydl_options(
        skip_download=True,
        quiet=True,
        no_warnings=True,
        noplaylist=True,
    )

    def operation() -> dict[str, Any]:
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(normalized_url, download=False)
        except DownloadError as exc:
            raise YouTubeDownloadError(
                "Не удалось получить метаданные YouTube-видео",
                details={
                    "youtube_url": normalized_url,
                    "retryable": not _is_non_retryable_download_error(exc),
                },
            ) from exc

        if not isinstance(info, dict):
            raise YouTubeDownloadError(
                "Не удалось получить метаданные видео",
                details={"youtube_url": normalized_url, "retryable": True},
            )

        title_raw = info.get("title")
        title = title_raw.strip() if isinstance(title_raw, str) and title_raw.strip() else None
        duration_seconds = _extract_duration_seconds(info.get("duration"))

        return {
            "title": title,
            "duration_seconds": duration_seconds,
        }

    try:
        return _run_youtube_with_retry("YouTube metadata", operation)
    except ClientValidationError:
        raise
    except YouTubeDownloadError:
        raise
    except Exception as exc:
        raise YouTubeDownloadError(
            "Не удалось получить метаданные YouTube-видео",
            details={"youtube_url": normalized_url, "retryable": True},
        ) from exc


def download_audio(youtube_url: str) -> str:
    """Скачивает и конвертирует аудио в mp3, возвращая путь к файлу."""
    normalized_url = _validate_youtube_url(youtube_url)
    logger.info("Начата загрузка аудио с YouTube")

    def operation() -> str:
        _clear_temp_folder()
        temp_dir = _create_temp_folder()
        output_template = os.path.join(temp_dir, "%(id)s.%(ext)s")

        ydl_opts = _build_ydl_options(
            format="bestaudio[ext=webm]/bestaudio",
            outtmpl=output_template,
            noplaylist=True,
        )

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(normalized_url, download=True)
                source_path = ydl.prepare_filename(info)
        except DownloadError as exc:
            raise YouTubeDownloadError(
                "Не удалось скачать аудио с YouTube",
                details={
                    "youtube_url": normalized_url,
                    "retryable": not _is_non_retryable_download_error(exc),
                },
            ) from exc

        if not source_path or not os.path.isfile(source_path):
            raise YouTubeDownloadError(
                "Временный аудиофайл не найден после загрузки",
                details={"youtube_url": normalized_url, "retryable": True},
            )

        video_id = info.get("id")
        if not isinstance(video_id, str) or not video_id.strip():
            raise YouTubeDownloadError(
                "Не удалось определить идентификатор видео",
                details={"youtube_url": normalized_url, "retryable": False},
            )

        mp3_path = os.path.join(temp_dir, f"{video_id}.mp3")
        try:
            subprocess.run(
                [
                    "ffmpeg", "-y", "-i", source_path,
                    "-vn",           # убираем видеодорожку, если вдруг осталась
                    "-ac", "1",      # моно (речь — 1 канал достаточно)
                    "-ar", "16000",  # 16 kHz — стандарт для ASR-моделей
                    "-b:a", "48k",   # 48 kbps — достаточно для разборчивости речи
                    mp3_path,
                ],
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as exc:
            raise YouTubeDownloadError(
                "Ошибка конвертации аудио в mp3",
                details={"stderr": (exc.stderr or "").strip()[:500], "retryable": False},
            ) from exc

        if not os.path.isfile(mp3_path):
            raise YouTubeDownloadError(
                "Файл mp3 не был создан",
                details={"youtube_url": normalized_url, "retryable": False},
            )

        if os.path.abspath(source_path) != os.path.abspath(mp3_path) and os.path.exists(source_path):
            os.remove(source_path)

        logger.info("Аудио успешно загружено и конвертировано")
        return mp3_path

    try:
        return _run_youtube_with_retry("YouTube audio download", operation)
    except ClientValidationError:
        raise
    except YouTubeDownloadError:
        raise
    except Exception as exc:
        raise YouTubeDownloadError(
            "Не удалось скачать аудио с YouTube",
            details={"youtube_url": normalized_url, "retryable": True},
        ) from exc
