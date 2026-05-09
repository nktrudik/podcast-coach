import streamlit as st

from frontend.api_client import BackendAPIClient
from frontend.ui.actions import create_session_for_video, send_chat_message
from frontend.ui.actions import select_session
from frontend.ui.catalog import (
    find_video,
    format_session_label,
    get_video_display_title,
    list_sessions_for_video,
    session_position_for_video,
)
from frontend.ui.components.sidebar import render_upload_form
from frontend.ui.state import as_positive_int

APP_TITLE = "English Podcast Coach"


def render_messages() -> None:
    """Отрисовывает историю сообщений в формате Streamlit chat UI."""
    for item in st.session_state.messages:
        role = "user" if item.get("role") == "user" else "assistant"
        content = str(item.get("content") or "")
        with st.chat_message(role):
            st.markdown(content)


def _render_header(selected_video_id: int | None, selected_session_id: int | None) -> None:
    """Рендерит верхнюю область активного видео и чата."""
    st.title(APP_TITLE)

    video = find_video(st.session_state.videos, selected_video_id)
    if video is None:
        return

    video_label = get_video_display_title(video)
    session_position = session_position_for_video(
        st.session_state.sessions,
        video_id=selected_video_id,
        session_id=selected_session_id,
    )
    session_label = f"Чат #{session_position}" if session_position is not None else "Чат не выбран"

    with st.container(border=True):
        left_col, right_col = st.columns([4, 1])
        with left_col:
            st.caption("Выбранное видео")
            st.markdown(f"### {video_label}")
        with right_col:
            st.caption("Сессия")
            st.markdown(f"**{session_label}**")


def _render_onboarding(client: BackendAPIClient) -> None:
    """Показывает стартовый экран с объяснением сервиса и загрузкой видео."""
    st.title(APP_TITLE)
    st.subheader(
        "Загрузи YouTube-подкаст или интервью на английском, получи транскрипт "
        "и обсуждай его с AI-коучем."
    )

    st.markdown("1. Вставь ссылку на YouTube-видео")
    st.markdown("2. Дождись обработки аудио и транскрипта")
    st.markdown("3. Обсуждай подкаст в чате на английском")

    st.divider()
    render_upload_form(client, key_prefix="main", button_label="Загрузить видео")


def _render_video_without_chat(client: BackendAPIClient, selected_video_id: int | None) -> None:
    """Показывает понятное состояние, когда активный чат не выбран."""
    if selected_video_id is None:
        return

    related_sessions = list_sessions_for_video(st.session_state.sessions, selected_video_id)

    with st.container(border=True):
        if related_sessions:
            st.subheader("Это видео уже есть в базе")
            st.caption("Выбери существующий чат или начни новый.")
            st.markdown("**История чатов по этому видео**")

            for index, session in enumerate(related_sessions, start=1):
                session_id = as_positive_int(session.get("id"))
                if session_id is None:
                    continue

                if st.button(
                    format_session_label(session, index),
                    key=f"main_choose_session_{session_id}",
                    use_container_width=True,
                ):
                    if select_session(client, session_id):
                        st.rerun()
        else:
            st.subheader("Чатов по этому видео пока нет")
            st.caption("Создай первый чат и начни обсуждать подкаст.")

        st.divider()
        if st.button("Создать новый чат", type="primary", use_container_width=True):
            if create_session_for_video(client, selected_video_id):
                st.rerun()


def render_chat_panel(client: BackendAPIClient) -> None:
    """Рендерит центральную чат-панель с историей и полем ввода."""
    selected_video_id = as_positive_int(st.session_state.selected_video_id)
    selected_session_id = as_positive_int(st.session_state.selected_session_id)

    if selected_video_id is None:
        _render_onboarding(client)
        return

    _render_header(selected_video_id, selected_session_id)

    if selected_session_id is None:
        _render_video_without_chat(client, selected_video_id)
        return
    else:
        render_messages()

    prompt = st.chat_input(
        "Можно задавать вопросы по подкасту",
        disabled=False,
    )
    if prompt:
        if send_chat_message(client, prompt):
            st.rerun()
