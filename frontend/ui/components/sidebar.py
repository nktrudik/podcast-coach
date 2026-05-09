import streamlit as st

from frontend.api_client import BackendAPIClient
from frontend.ui.actions import (
    create_session_for_video,
    process_video_upload,
    refresh_state,
    select_session,
    select_video,
)
from frontend.ui.catalog import format_session_label, format_video_label, group_sessions_by_video
from frontend.ui.state import as_positive_int


def render_upload_block(client: BackendAPIClient) -> None:
    """Рендерит отдельный блок загрузки нового видео в sidebar."""
    if st.session_state.get("pending_reset_upload_toggle"):
        st.session_state.allow_new_video_upload = False
        st.session_state.pending_reset_upload_toggle = False
    if st.session_state.get("pending_reset_youtube_url"):
        st.session_state.youtube_url = ""
        st.session_state.pending_reset_youtube_url = False

    with st.expander("Добавить новое видео", expanded=not st.session_state.videos):
        st.info("Поддерживаются только видео длительностью до 30 минут.")

        selected_video_id = as_positive_int(st.session_state.selected_video_id)

        if selected_video_id is None:
            st.caption("Загрузи новое видео и сразу открой чат.")
            allow_upload = True
        else:
            st.caption(
                f"Сейчас выбран видео #{selected_video_id}. Для нового чата по нему используй кнопку "
                "\"Новый чат для этого видео\" ниже."
            )
            allow_upload = st.checkbox(
                "Хочу загрузить другое видео",
                key="allow_new_video_upload",
            )

        st.text_input(
            "Ссылка на YouTube",
            key="youtube_url",
            placeholder="https://www.youtube.com/watch?v=...",
            disabled=not allow_upload,
        )

        if st.button(
            "Загрузить и открыть чат",
            key="upload_video_button",
            use_container_width=True,
            disabled=not allow_upload,
        ):
            if process_video_upload(client):
                st.rerun()


def render_video_tree(client: BackendAPIClient) -> None:
    """Рендерит иерархию видео и связанных чат-сессий."""
    videos = st.session_state.videos
    sessions = st.session_state.sessions

    if not videos:
        st.info("Список видео пуст. Загрузи первое видео.")
        return

    sessions_by_video = group_sessions_by_video(sessions)

    for video in videos:
        video_id = as_positive_int(video.get("id"))
        if video_id is None:
            continue

        related_sessions = sessions_by_video.get(video_id, [])
        is_selected_video = video_id == st.session_state.selected_video_id

        title = format_video_label(video)
        if related_sessions:
            title = f"{title} ({len(related_sessions)})"

        with st.expander(title, expanded=is_selected_video):
            if st.button(
                "Выбрать видео",
                key=f"choose_video_{video_id}",
                use_container_width=True,
            ):
                if select_video(client, video_id):
                    st.rerun()

            if not related_sessions:
                st.caption("У этого видео пока нет чат-сессий")
            else:
                for session in related_sessions:
                    session_id = as_positive_int(session.get("id"))
                    if session_id is None:
                        continue

                    is_selected_session = session_id == st.session_state.selected_session_id
                    if st.button(
                        format_session_label(session),
                        key=f"choose_session_{session_id}",
                        use_container_width=True,
                        type="primary" if is_selected_session else "secondary",
                    ):
                        if select_session(client, session_id):
                            st.rerun()

            if st.button(
                "Новый чат для этого видео",
                key=f"new_chat_for_video_{video_id}",
                use_container_width=True,
            ):
                if create_session_for_video(client, video_id):
                    st.rerun()


def render_sidebar(client: BackendAPIClient) -> None:
    """Рендерит sidebar в стиле ChatGPT: управление видео и чатами."""
    with st.sidebar:
        st.header("Видео и чаты")

        if st.button("Обновить список", use_container_width=True):
            if refresh_state(client):
                st.rerun()

        render_upload_block(client)
        st.divider()
        render_video_tree(client)
