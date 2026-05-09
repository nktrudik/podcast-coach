from collections import defaultdict
from typing import Any

from frontend.ui.state import as_positive_int


def format_video_label(video: dict[str, Any]) -> str:
    """Формирует читаемое имя видео для sidebar."""
    video_id = as_positive_int(video.get("id"))
    title = str(video.get("title") or "").strip()
    youtube_video_id = str(video.get("youtube_video_id") or "").strip()

    if len(title) > 70:
        title = f"{title[:67]}..."

    if title:
        return f"Видео #{video_id} · {title}"

    if youtube_video_id:
        return f"Видео #{video_id} · {youtube_video_id}"
    return f"Видео #{video_id}"


def format_session_label(session: dict[str, Any]) -> str:
    """Формирует подпись чат-сессии для списка."""
    session_id = as_positive_int(session.get("id"))
    title = str(session.get("title") or "").strip()
    created_at = str(session.get("created_at") or "").strip()

    base_label = title if title else f"Чат #{session_id}"
    return f"{base_label} · {created_at}" if created_at else base_label


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

    if selected_video_id is None and video_ids:
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
        if sessions_for_video:
            selected_session_id = as_positive_int(sessions_for_video[0].get("id"))
        else:
            selected_session_id = None

    return selected_video_id, selected_session_id
