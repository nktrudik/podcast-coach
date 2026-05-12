import os
import shutil
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

RENDER_SECRETS_DIR = "/etc/secrets"
DOCKER_SECRETS_DIR = "/app/secrets"


def _default_js_runtimes() -> dict[str, dict[str, str]]:
    """Возвращает JS runtimes для YouTube challenge solving."""
    return {"deno": {}, "node": {}}


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
        "requested format is not available",
        "sign in to confirm",
        "confirm you're not a bot",
        "confirm you’re not a bot",
        "not a bot",
    )
    return any(marker in message for marker in non_retryable_markers)


def _requires_youtube_auth(exc: DownloadError) -> bool:
    """Определяет ошибки, где YouTube явно требует cookies/авторизацию."""
    message = str(exc).lower()
    auth_markers = (
        "sign in to confirm",
        "confirm you're not a bot",
        "confirm you’re not a bot",
        "not a bot",
        "use --cookies",
        "use --cookies-from-browser",
    )
    return any(marker in message for marker in auth_markers)


def _is_format_unavailable_error(exc: DownloadError) -> bool:
    """Определяет ошибку выбора недоступного медиаформата."""
    return "requested format is not available" in str(exc).lower()


def _get_cookie_path_candidates(configured_path: str) -> list[str]:
    """Возвращает безопасный список путей, где может лежать cookies-файл."""
    expanded_path = os.path.expandvars(os.path.expanduser(configured_path))
    if os.path.isabs(expanded_path):
        return [expanded_path]

    return [
        expanded_path,
        os.path.join(RENDER_SECRETS_DIR, expanded_path),
        os.path.join(DOCKER_SECRETS_DIR, expanded_path),
    ]


def _resolve_youtube_cookies_file(configured_path: str) -> tuple[str | None, list[str]]:
    """Ищет cookies-файл по указанному пути и стандартным secret-директориям."""
    candidates = _get_cookie_path_candidates(configured_path)
    for candidate in candidates:
        if os.path.isfile(candidate):
            return candidate, candidates
    return None, candidates


def _prepare_youtube_cookies_file(cookies_file: str) -> str:
    """Копирует cookies в рабочий файл, который yt-dlp может обновлять."""
    temp_dir = _create_temp_folder()
    working_copy = os.path.join(temp_dir, "youtube_cookies_working.txt")
    shutil.copyfile(cookies_file, working_copy)
    return working_copy


def _build_ydl_options(**base_options: Any) -> dict[str, Any]:
    """Собирает yt-dlp options и безопасно подключает cookies, если они заданы."""
    ydl_opts = dict(base_options)
    # yt-dlp по умолчанию включает только Deno, а Docker-образ ставит Node.js.
    ydl_opts.setdefault("js_runtimes", _default_js_runtimes())
    configured_cookies_file = (
        settings.youtube_cookies_file.strip() if settings.youtube_cookies_file else ""
    )
    cookies_configured = bool(configured_cookies_file)

    if not cookies_configured:
        logger.info("YouTube cookies enabled: False")
        return ydl_opts

    cookies_file, checked_paths = _resolve_youtube_cookies_file(configured_cookies_file)
    if cookies_file is None:
        raise YouTubeDownloadError(
            "Файл YouTube cookies не найден",
            details={
                "cookies_configured": True,
                "configured_path": configured_cookies_file,
                "checked_paths": checked_paths,
                "retryable": False,
            },
        )

    try:
        ydl_opts["cookiefile"] = _prepare_youtube_cookies_file(cookies_file)
    except OSError as exc:
        raise YouTubeDownloadError(
            "Не удалось подготовить файл YouTube cookies",
            details={
                "cookies_configured": True,
                "configured_path": configured_cookies_file,
                "retryable": False,
            },
        ) from exc

    logger.info("YouTube cookies enabled: True")
    return ydl_opts


def _build_download_error(
    default_message: str,
    *,
    youtube_url: str,
    exc: DownloadError,
    ydl_opts: dict[str, Any],
) -> YouTubeDownloadError:
    """Создает понятную ошибку YouTube без утечки содержимого cookies."""
    cookies_active = bool(ydl_opts.get("cookiefile"))
    retryable = not _is_non_retryable_download_error(exc)
    details: dict[str, Any] = {
        "youtube_url": youtube_url,
        "retryable": retryable,
        "cookies_configured": bool(settings.youtube_cookies_file),
        "cookies_active": cookies_active,
    }

    if _requires_youtube_auth(exc):
        if cookies_active:
            message = (
                "YouTube не принял cookies. Проверь, что файл экспортирован из "
                "авторизованного браузера и не устарел"
            )
        else:
            message = "YouTube требует cookies, но файл cookies не подключен"
        details["retryable"] = False
    elif _is_format_unavailable_error(exc):
        message = (
            "YouTube не отдал доступный аудиоформат для этого видео. "
            "Попробуй обновить yt-dlp или использовать другую ссылку"
        )
        details["retryable"] = False
    else:
        message = default_message

    return YouTubeDownloadError(message, details=details)


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


def _get_selected_download_format(info: dict[str, Any]) -> dict[str, Any]:
    """Возвращает формат, который yt-dlp фактически выбрал для скачивания."""
    requested_downloads = info.get("requested_downloads")
    if isinstance(requested_downloads, list) and requested_downloads:
        selected = requested_downloads[0]
        if isinstance(selected, dict):
            return selected

    return info


def _log_selected_download_format(info: dict[str, Any]) -> None:
    """Логирует выбранный YouTube-формат для диагностики размера загрузки."""
    selected_format = _get_selected_download_format(info)
    format_id = selected_format.get("format_id")
    ext = selected_format.get("ext")
    acodec = selected_format.get("acodec")
    vcodec = selected_format.get("vcodec")
    filesize = selected_format.get("filesize")
    filesize_approx = selected_format.get("filesize_approx")

    logger.info(
        "Выбран YouTube format: format_id=%s ext=%s acodec=%s vcodec=%s "
        "filesize=%s filesize_approx=%s",
        format_id,
        ext,
        acodec,
        vcodec,
        filesize,
        filesize_approx,
    )
    if vcodec and vcodec != "none":
        logger.warning(
            "Выбран не audio-only YouTube format: format_id=%s ext=%s "
            "acodec=%s vcodec=%s",
            format_id,
            ext,
            acodec,
            vcodec,
        )


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
                info = ydl.extract_info(normalized_url, download=False, process=False)
        except DownloadError as exc:
            raise _build_download_error(
                "Не удалось получить метаданные YouTube-видео",
                youtube_url=normalized_url,
                exc=exc,
                ydl_opts=ydl_opts,
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
            format=(
                "bestaudio[acodec!=none][vcodec=none]/"
                "bestaudio[acodec!=none]/"
                "worstaudio[acodec!=none]"
            ),
            outtmpl=output_template,
            noplaylist=True,
        )

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(normalized_url, download=True)
                if isinstance(info, dict):
                    _log_selected_download_format(info)
                source_path = ydl.prepare_filename(info)
        except DownloadError as exc:
            raise _build_download_error(
                "Не удалось скачать аудио с YouTube",
                youtube_url=normalized_url,
                exc=exc,
                ydl_opts=ydl_opts,
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
