import os
import shutil
import subprocess  # nosec B404
import time
from collections.abc import Callable, Mapping

import yt_dlp
from yt_dlp.utils import DownloadError

from app.clients.errors import ClientValidationError, YouTubeDownloadError
from app.clients.youtube_options import (
    AUDIO_ONLY_FORMAT_SELECTOR,
    SMALLEST_AUDIO_FALLBACK_FORMAT_SELECTOR,
    build_ydl_options,
    youtube_audio_extractor_args,
    youtube_fallback_extractor_args,
)
from app.core.config import settings
from app.core.logger import get_logger
from app.core.types import JsonValue
from app.core.youtube import normalize_youtube_url

logger = get_logger(__name__)


def _run_youtube_with_retry[ResultT](
    operation_name: str,
    operation: Callable[[], ResultT],
) -> ResultT:
    """Run a YouTube operation with retries for transient errors."""
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
                "%s transient error on attempt %s/%s",
                operation_name,
                attempt,
                settings.youtube_max_retries,
            )
            if settings.youtube_retry_delay_seconds > 0:
                time.sleep(settings.youtube_retry_delay_seconds)

    if last_exc is not None:
        raise last_exc

    raise RuntimeError("Invalid YouTube retry state")


def _create_temp_folder() -> str:
    """Create the temporary media folder and return its path."""
    temp_dir = os.path.join(".", "temp")
    os.makedirs(temp_dir, exist_ok=True)
    return temp_dir


def _clear_temp_folder() -> None:
    """Clear temporary files before a new download attempt."""
    temp_dir = _create_temp_folder()
    for filename in os.listdir(temp_dir):
        file_path = os.path.join(temp_dir, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.remove(file_path)
        except OSError as exc:
            logger.warning("Failed to delete a temporary file before retry: %s", exc)


def _is_non_retryable_download_error(exc: DownloadError) -> bool:
    """Return whether a YouTube error should not be retried immediately."""
    message = str(exc).lower()
    non_retryable_markers = (
        "403",
        "429",
        "forbidden",
        "too many requests",
        "requested format is not available",
        "sign in to confirm",
        "confirm you're not a bot",
        "confirm you\u2019re not a bot",
        "not a bot",
    )
    return any(marker in message for marker in non_retryable_markers)


def _requires_youtube_auth(exc: DownloadError) -> bool:
    """Return whether YouTube explicitly asks for cookies or authentication."""
    message = str(exc).lower()
    auth_markers = (
        "sign in to confirm",
        "confirm you're not a bot",
        "confirm you\u2019re not a bot",
        "not a bot",
        "use --cookies",
        "use --cookies-from-browser",
    )
    return any(marker in message for marker in auth_markers)


def _is_format_unavailable_error(exc: DownloadError) -> bool:
    """Return whether the selected media format is unavailable."""
    return "requested format is not available" in str(exc).lower()


def _resolve_ffmpeg_path() -> str:
    """Find the FFmpeg executable and return an absolute path."""
    ffmpeg_path = shutil.which("ffmpeg")
    if not ffmpeg_path:
        raise YouTubeDownloadError(
            "FFmpeg was not found in PATH",
            details={"retryable": False},
        )

    return os.path.abspath(ffmpeg_path)


def _build_download_error(
    default_message: str,
    *,
    youtube_url: str,
    exc: DownloadError,
    ydl_opts: Mapping[str, object],
) -> YouTubeDownloadError:
    """Create a safe YouTube error without leaking cookies content."""
    cookies_active = bool(ydl_opts.get("cookiefile"))
    retryable = not _is_non_retryable_download_error(exc)
    details: dict[str, JsonValue] = {
        "youtube_url": youtube_url,
        "retryable": retryable,
        "cookies_configured": bool(settings.youtube_cookies_file),
        "cookies_active": cookies_active,
    }

    if _requires_youtube_auth(exc):
        if cookies_active:
            message = (
                "YouTube rejected the cookies file. Export fresh cookies from an "
                "authenticated browser and try again."
            )
        else:
            message = "YouTube requires cookies, but no cookies file is configured."
        details["retryable"] = False
    elif _is_format_unavailable_error(exc):
        message = (
            "YouTube did not provide an available audio format for this video. "
            "Try a different link or update yt-dlp."
        )
        details["retryable"] = False
    else:
        message = default_message

    return YouTubeDownloadError(message, details=details)


def _validate_youtube_url(youtube_url: str) -> str:
    """Validate a non-empty YouTube URL."""
    if not isinstance(youtube_url, str):
        raise ClientValidationError("YouTube URL must be a string")

    normalized_url = youtube_url.strip()
    if not normalized_url:
        raise ClientValidationError("YouTube URL must not be empty")

    try:
        canonical_url, _ = normalize_youtube_url(normalized_url)
    except Exception as exc:
        raise ClientValidationError("Only valid YouTube URLs are supported") from exc

    return canonical_url


def _extract_duration_seconds(raw_value: object) -> int | None:
    """Extract duration in seconds from yt-dlp metadata."""
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


def _string_key_dict(value: Mapping[object, object]) -> dict[str, object]:
    """Convert a mapping returned by yt-dlp to a string-key dictionary."""
    return {str(key): item for key, item in value.items()}


def _get_selected_download_format(info: Mapping[str, object]) -> dict[str, object]:
    """Return the format yt-dlp selected for the actual download."""
    requested_downloads = info.get("requested_downloads")
    if isinstance(requested_downloads, list) and requested_downloads:
        selected = requested_downloads[0]
        if isinstance(selected, dict):
            return _string_key_dict(selected)

    return dict(info)


def _log_selected_download_format(info: Mapping[str, object]) -> None:
    """Log the selected YouTube format for download-size diagnostics."""
    selected_format = _get_selected_download_format(info)
    format_id = selected_format.get("format_id")
    ext = selected_format.get("ext")
    acodec = selected_format.get("acodec")
    vcodec = selected_format.get("vcodec")
    filesize = selected_format.get("filesize")
    filesize_approx = selected_format.get("filesize_approx")

    logger.info(
        "Selected YouTube format: format_id=%s ext=%s acodec=%s vcodec=%s "
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
            "Selected a non audio-only YouTube format: format_id=%s ext=%s "
            "acodec=%s vcodec=%s",
            format_id,
            ext,
            acodec,
            vcodec,
        )


def _download_youtube_format(
    normalized_url: str,
    ydl_opts: Mapping[str, object],
) -> tuple[dict[str, object], str]:
    """Download a YouTube format and return metadata plus the temp file path."""
    with yt_dlp.YoutubeDL(dict(ydl_opts)) as ydl:
        raw_info = ydl.extract_info(normalized_url, download=True)
        if not isinstance(raw_info, dict):
            raise YouTubeDownloadError(
                "YouTube returned invalid data after download",
                details={"youtube_url": normalized_url, "retryable": True},
            )
        info = _string_key_dict(raw_info)
        source_path = ydl.prepare_filename(raw_info)

    _log_selected_download_format(info)
    return info, source_path


def get_video_metadata(youtube_url: str) -> dict[str, object]:
    """Return YouTube video metadata: title and duration_seconds."""
    normalized_url = _validate_youtube_url(youtube_url)

    ydl_opts = build_ydl_options(
        skip_download=True,
        quiet=True,
        no_warnings=True,
        noplaylist=True,
    )

    def operation() -> dict[str, object]:
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                raw_info = ydl.extract_info(
                    normalized_url, download=False, process=False
                )
        except DownloadError as exc:
            raise _build_download_error(
                "Failed to fetch YouTube video metadata",
                youtube_url=normalized_url,
                exc=exc,
                ydl_opts=ydl_opts,
            ) from exc

        if not isinstance(raw_info, dict):
            raise YouTubeDownloadError(
                "Failed to fetch video metadata",
                details={"youtube_url": normalized_url, "retryable": True},
            )

        info = _string_key_dict(raw_info)
        title_raw = info.get("title")
        title = (
            title_raw.strip()
            if isinstance(title_raw, str) and title_raw.strip()
            else None
        )
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
            "Failed to fetch YouTube video metadata",
            details={"youtube_url": normalized_url, "retryable": True},
        ) from exc


def download_audio(youtube_url: str) -> str:
    """Download and convert audio to mp3, returning the local file path."""
    normalized_url = _validate_youtube_url(youtube_url)
    logger.info("Starting YouTube audio download")

    def operation() -> str:
        _clear_temp_folder()
        temp_dir = _create_temp_folder()
        output_template = os.path.join(temp_dir, "%(id)s.%(ext)s")

        ydl_opts = build_ydl_options(
            format=AUDIO_ONLY_FORMAT_SELECTOR,
            outtmpl=output_template,
            extractor_args=youtube_audio_extractor_args(),
            noplaylist=True,
        )

        try:
            info, source_path = _download_youtube_format(normalized_url, ydl_opts)
        except DownloadError as exc:
            if not _is_format_unavailable_error(exc):
                raise _build_download_error(
                    "Failed to download audio from YouTube",
                    youtube_url=normalized_url,
                    exc=exc,
                    ydl_opts=ydl_opts,
                ) from exc

            logger.warning(
                "YouTube did not provide an audio-only format; trying the smallest "
                "available format with an audio stream"
            )
            fallback_ydl_opts = build_ydl_options(
                format=SMALLEST_AUDIO_FALLBACK_FORMAT_SELECTOR,
                outtmpl=output_template,
                extractor_args=youtube_fallback_extractor_args(),
                noplaylist=True,
            )
            try:
                info, source_path = _download_youtube_format(
                    normalized_url, fallback_ydl_opts
                )
            except DownloadError as fallback_exc:
                raise _build_download_error(
                    "Failed to download audio from YouTube",
                    youtube_url=normalized_url,
                    exc=fallback_exc,
                    ydl_opts=fallback_ydl_opts,
                ) from fallback_exc

        if not source_path or not os.path.isfile(source_path):
            raise YouTubeDownloadError(
                "Temporary audio file was not found after download",
                details={"youtube_url": normalized_url, "retryable": True},
            )

        video_id = info.get("id")
        if not isinstance(video_id, str) or not video_id.strip():
            raise YouTubeDownloadError(
                "Failed to detect the YouTube video id",
                details={"youtube_url": normalized_url, "retryable": False},
            )

        ffmpeg_path = _resolve_ffmpeg_path()
        mp3_path = os.path.join(temp_dir, f"{video_id}.mp3")
        try:
            subprocess.run(  # nosec B603  # noqa: S603
                [
                    ffmpeg_path,
                    "-y",
                    "-i",
                    source_path,
                    "-vn",
                    "-ac",
                    "1",
                    "-ar",
                    "16000",
                    "-b:a",
                    "48k",
                    mp3_path,
                ],
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as exc:
            raise YouTubeDownloadError(
                "Failed to convert audio to mp3",
                details={
                    "stderr": (exc.stderr or "").strip()[:500],
                    "retryable": False,
                },
            ) from exc

        if not os.path.isfile(mp3_path):
            raise YouTubeDownloadError(
                "The mp3 file was not created",
                details={"youtube_url": normalized_url, "retryable": False},
            )

        if os.path.abspath(source_path) != os.path.abspath(mp3_path) and os.path.exists(
            source_path
        ):
            os.remove(source_path)

        logger.info("Audio downloaded and converted successfully")
        return mp3_path

    try:
        return _run_youtube_with_retry("YouTube audio download", operation)
    except ClientValidationError:
        raise
    except YouTubeDownloadError:
        raise
    except Exception as exc:
        raise YouTubeDownloadError(
            "Failed to download audio from YouTube",
            details={"youtube_url": normalized_url, "retryable": True},
        ) from exc
