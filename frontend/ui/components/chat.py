import streamlit as st

from frontend.api_client import BackendAPIClient
from frontend.ui.actions import send_chat_message
from frontend.ui.state import as_positive_int


def render_messages() -> None:
    """Отрисовывает историю сообщений в формате Streamlit chat UI."""
    for item in st.session_state.messages:
        role = "user" if item.get("role") == "user" else "assistant"
        content = str(item.get("content") or "")
        with st.chat_message(role):
            st.markdown(content)


def _resolve_selected_video_title(selected_video_id: int | None) -> str:
    """Возвращает заголовок выбранного видео для верхней подписи чат-панели."""
    if selected_video_id is None:
        return "Видео не выбрано"

    for video in st.session_state.videos:
        video_id = as_positive_int(video.get("id"))
        if video_id != selected_video_id:
            continue

        title = str(video.get("title") or "").strip()
        if title:
            return title

        youtube_video_id = str(video.get("youtube_video_id") or "").strip()
        if youtube_video_id:
            return youtube_video_id

        return f"Видео #{selected_video_id}"

    return f"Видео #{selected_video_id}"


def render_chat_panel(client: BackendAPIClient) -> None:
    """Рендерит центральную чат-панель с историей и полем ввода."""
    selected_video_id = as_positive_int(st.session_state.selected_video_id)
    selected_session_id = as_positive_int(st.session_state.selected_session_id)

    video_title = _resolve_selected_video_title(selected_video_id)

    if selected_session_id is not None:
        st.caption(f"Выбрано: {video_title} · Сессия #{selected_session_id}")
    else:
        st.caption(f"Выбрано: {video_title}")

    render_messages()

    prompt = st.chat_input(
        "Напиши сообщение по выбранному видео",
        disabled=selected_session_id is None,
    )
    if prompt and selected_session_id is not None:
        if send_chat_message(client, prompt):
            st.rerun()
