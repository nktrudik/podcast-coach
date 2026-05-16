from collections import defaultdict
from typing import Any

from frontend.ui.state import as_positive_int


def _shorten(value: str, limit: int = 56) -> str:
    """Обрезает длинные подписи для компактного sidebar."""
    normalized = value.strip()
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[: limit - 3]}..."


def get_video_display_title(video: dict[str, Any], *, fallback_id: bool = True) -> str:
    """Возвращает полное человекочитаемое название видео."""
    video_id = as_positive_int(video.get("id"))
    title = str(video.get("title") or "").strip()
    youtube_url = str(video.get("youtube_url") or "").strip()
    youtube_video_id = str(video.get("youtube_video_id") or "").strip()

    if title:
        return title

    if youtube_url:
        return youtube_url

    if youtube_video_id:
        return youtube_video_id

    if fallback_id and video_id is not None:
        return f"Technical video #{video_id}"

    return "Untitled technical video"


def format_video_label(video: dict[str, Any]) -> str:
    """Формирует компактное имя видео для sidebar."""
    return _shorten(get_video_display_title(video))


def format_video_caption(video: dict[str, Any]) -> str:
    """Возвращает дополнительную подпись с полным URL/названием."""
    title = str(video.get("title") or "").strip()
    youtube_url = str(video.get("youtube_url") or "").strip()

    if title and youtube_url:
        return youtube_url
    return get_video_display_title(video)


def format_session_label(session: dict[str, Any], position: int | None = None) -> str:
    """Формирует подпись чат-сессии для списка."""
    title = str(session.get("title") or "").strip()
    created_at = str(session.get("created_at") or "").strip()

    base_label = (
        _shorten(title, 44)
        if title
        else f"Practice #{position}"
        if position
        else "Interview practice"
    )
    return f"{base_label} · {created_at}" if created_at else base_label


def find_video(videos: list[dict[str, Any]], video_id: int | None) -> dict[str, Any] | None:
    """Возвращает видео из списка по id."""
    if video_id is None:
        return None

    for video in videos:
        if as_positive_int(video.get("id")) == video_id:
            return video
    return None


def session_position_for_video(
    sessions: list[dict[str, Any]],
    *,
    video_id: int | None,
    session_id: int | None,
) -> int | None:
    """Возвращает порядковый номер сессии внутри выбранного видео."""
    if video_id is None or session_id is None:
        return None

    sessions_for_video = [
        session
        for session in sessions
        if as_positive_int(session.get("video_id")) == video_id
    ]
    for index, session in enumerate(sessions_for_video, start=1):
        if as_positive_int(session.get("id")) == session_id:
            return index
    return None


def list_sessions_for_video(
    sessions: list[dict[str, Any]],
    video_id: int | None,
) -> list[dict[str, Any]]:
    """Возвращает чат-сессии выбранного видео в порядке, пришедшем из backend."""
    if video_id is None:
        return []

    return [
        session
        for session in sessions
        if as_positive_int(session.get("video_id")) == video_id
    ]


def group_sessions_by_video(sessions: list[dict[str, Any]]) -> dict[int, list[dict[str, Any]]]:
    """Группирует чат-сессии по идентификатору видео."""
    grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for session in sessions:
        video_id = as_positive_int(session.get("video_id"))
        if video_id is None:
            continue
        grouped[video_id].append(session)
    return dict(grouped)


def resolve_selection(
    videos: list[dict[str, Any]],
    sessions: list[dict[str, Any]],
    preferred_video_id: int | None,
    preferred_session_id: int | None,
    *,
    auto_select_video: bool = True,
    auto_select_session: bool = True,
) -> tuple[int | None, int | None]:
    """Определяет валидную пару выбранных видео и сессии из данных backend."""
    video_ids = [video_id for video in videos if (video_id := as_positive_int(video.get("id"))) is not None]
    session_by_id = {
        session_id: session
        for session in sessions
        if (session_id := as_positive_int(session.get("id"))) is not None
    }

    selected_video_id = preferred_video_id if preferred_video_id in video_ids else None
    selected_session_id = preferred_session_id if preferred_session_id in session_by_id else None

    if selected_session_id is not None:
        session_video_id = as_positive_int(session_by_id[selected_session_id].get("video_id"))
        if session_video_id in video_ids:
            selected_video_id = session_video_id

    if selected_video_id is None and auto_select_video and video_ids:
        selected_video_id = video_ids[0]

    sessions_for_video = [
        session
        for session in sessions
        if as_positive_int(session.get("video_id")) == selected_video_id
    ]
    valid_session_ids = {
        session_id
        for session in sessions_for_video
        if (session_id := as_positive_int(session.get("id"))) is not None
    }

    if selected_session_id not in valid_session_ids:
        if auto_select_session and sessions_for_video:
            selected_session_id = as_positive_int(sessions_for_video[0].get("id"))
        else:
            selected_session_id = None

    return selected_video_id, selected_session_id
