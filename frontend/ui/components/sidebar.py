import streamlit as st

from frontend.api_client import BackendAPIClient
from frontend.ui.actions import (
    create_session_for_video,
    process_video_upload,
    refresh_state,
    select_session,
    select_video,
)
from frontend.ui.catalog import (
    format_session_label,
    format_video_caption,
    format_video_label,
    group_sessions_by_video,
)
from frontend.ui.state import as_positive_int


def render_upload_form(
    client: BackendAPIClient,
    *,
    key_prefix: str,
    button_label: str = "Add technical video",
) -> None:
    """Рендерит форму загрузки YouTube-видео."""
    input_key = f"{key_prefix}_youtube_url"
    pending_reset_keys = st.session_state.get("pending_reset_input_keys", [])
    if input_key in pending_reset_keys:
        st.session_state[input_key] = ""
        st.session_state.pending_reset_input_keys = [
            key for key in pending_reset_keys if key != input_key
        ]

    st.text_input(
        "YouTube URL",
        key=input_key,
        placeholder="https://www.youtube.com/watch?v=...",
        label_visibility="collapsed",
    )

    if st.button(
        button_label,
        key=f"{key_prefix}_upload_video_button",
        use_container_width=True,
        type="primary",
    ):
        if process_video_upload(client, state_key=input_key):
            st.rerun()


def render_upload_block(client: BackendAPIClient) -> None:
    """Рендерит блок загрузки нового видео в sidebar."""
    if st.session_state.get("pending_reset_upload_toggle"):
        st.session_state.allow_new_video_upload = False
        st.session_state.pending_reset_upload_toggle = False
    if st.session_state.get("pending_reset_youtube_url"):
        st.session_state.youtube_url = ""
        st.session_state.pending_reset_youtube_url = False

    with st.expander("Add technical video", expanded=False):
        st.caption(
            "Paste a technical YouTube video. After processing, start interview practice."
        )
        render_upload_form(
            client, key_prefix="sidebar", button_label="Add technical video"
        )


def render_video_tree(client: BackendAPIClient) -> None:
    """Рендерит иерархию видео и связанных чат-сессий."""
    videos = st.session_state.videos
    sessions = st.session_state.sessions

    if not videos:
        st.info("No technical videos yet. Add your first technical video.")
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
            full_caption = format_video_caption(video)
            if full_caption:
                st.caption(full_caption)

            if st.button(
                "Select video",
                key=f"choose_video_{video_id}",
                use_container_width=True,
                type="primary"
                if is_selected_video and st.session_state.selected_session_id is None
                else "secondary",
            ):
                if select_video(client, video_id):
                    st.rerun()

            if not related_sessions:
                st.caption("No interview practice sessions yet.")
            else:
                st.caption("Interview practice sessions")
                for index, session in enumerate(related_sessions, start=1):
                    session_id = as_positive_int(session.get("id"))
                    if session_id is None:
                        continue

                    is_selected_session = (
                        session_id == st.session_state.selected_session_id
                    )
                    if st.button(
                        format_session_label(session, index),
                        key=f"choose_session_{session_id}",
                        use_container_width=True,
                        type="primary" if is_selected_session else "secondary",
                    ):
                        if select_session(client, session_id):
                            st.rerun()

            if st.button(
                "New interview practice",
                key=f"new_chat_for_video_{video_id}",
                use_container_width=True,
            ):
                if create_session_for_video(client, video_id):
                    st.rerun()


def render_sidebar(client: BackendAPIClient) -> None:
    """Рендерит sidebar в стиле ChatGPT: управление видео и чатами."""
    with st.sidebar:
        st.title("English Interview Coach")
        st.caption("IT English interview practice")

        render_upload_block(client)
        if st.button("Refresh", use_container_width=True):
            if refresh_state(client):
                st.rerun()

        st.divider()
        st.caption("Technical videos")
        render_video_tree(client)
