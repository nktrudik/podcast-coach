import os
import shutil

from app.clients.errors import YouTubeDownloadError
from app.core.config import settings
from app.core.logger import get_logger
from app.core.types import JsonValue

logger = get_logger(__name__)

RENDER_SECRETS_DIR = "/etc/secrets"
DOCKER_SECRETS_DIR = "/app/secrets"
AUDIO_ONLY_FORMAT_SELECTOR = (
    "bestaudio[acodec!=none][vcodec=none]/"
    "bestaudio[acodec!=none]/"
    "worstaudio[acodec!=none]"
)
SMALLEST_AUDIO_FALLBACK_FORMAT_SELECTOR = (
    f"{AUDIO_ONLY_FORMAT_SELECTOR}/worst[acodec!=none]"
)


def youtube_audio_extractor_args() -> dict[str, dict[str, list[str]]]:
    """Return YouTube extractor args for stable audio-only results."""
    return {
        "youtube": {
            "player_client": ["tv_downgraded"],
            "player_skip": ["webpage", "initial_data"],
        }
    }


def youtube_fallback_extractor_args() -> dict[str, dict[str, list[str]]]:
    """Return YouTube extractor args for a small muxed fallback format."""
    return {
        "youtube": {
            "player_client": ["tv_downgraded", "web_safari"],
            "player_skip": ["webpage"],
        }
    }


def build_ydl_options(**base_options: object) -> dict[str, object]:
    """Build yt-dlp options and safely attach cookies when configured."""
    ydl_opts = dict(base_options)
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
        checked_paths_json: list[JsonValue] = []
        for checked_path in checked_paths:
            checked_paths_json.append(checked_path)
        raise YouTubeDownloadError(
            "YouTube cookies file was not found",
            details={
                "cookies_configured": True,
                "configured_path": configured_cookies_file,
                "checked_paths": checked_paths_json,
                "retryable": False,
            },
        )

    try:
        ydl_opts["cookiefile"] = _prepare_youtube_cookies_file(cookies_file)
    except OSError as exc:
        raise YouTubeDownloadError(
            "Failed to prepare the YouTube cookies file",
            details={
                "cookies_configured": True,
                "configured_path": configured_cookies_file,
                "retryable": False,
            },
        ) from exc

    logger.info("YouTube cookies enabled: True")
    return ydl_opts


def _default_js_runtimes() -> dict[str, dict[str, str]]:
    """Return JS runtimes for YouTube challenge solving."""
    return {"deno": {}, "node": {}}


def _get_cookie_path_candidates(configured_path: str) -> list[str]:
    """Return safe candidate paths for a configured cookies file."""
    expanded_path = os.path.expandvars(os.path.expanduser(configured_path))
    if os.path.isabs(expanded_path):
        return [expanded_path]

    return [
        expanded_path,
        os.path.join(RENDER_SECRETS_DIR, expanded_path),
        os.path.join(DOCKER_SECRETS_DIR, expanded_path),
    ]


def _resolve_youtube_cookies_file(configured_path: str) -> tuple[str | None, list[str]]:
    """Find a cookies file by configured path and known secret directories."""
    candidates = _get_cookie_path_candidates(configured_path)
    for candidate in candidates:
        if os.path.isfile(candidate):
            return candidate, candidates
    return None, candidates


def _prepare_youtube_cookies_file(cookies_file: str) -> str:
    """Copy cookies to a working file that yt-dlp can update."""
    temp_dir = os.path.join(".", "temp")
    os.makedirs(temp_dir, exist_ok=True)
    working_copy = os.path.join(temp_dir, "youtube_cookies_working.txt")
    shutil.copyfile(cookies_file, working_copy)
    return working_copy
