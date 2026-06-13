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

APP_TITLE = "English Interview Coach for IT"
WELCOME_TITLE = "Practice English for IT interviews with any technical YouTube video"
WELCOME_SUBTITLE = (
    "Загрузи техническое видео, а AI-коуч поможет обсудить его на английском "
    "как на собеседовании: задаст вопросы, поправит ошибки, подскажет лексику "
    "и поможет сформулировать сильные ответы."
)
EXAMPLE_COMMANDS = [
    "Ask me interview questions about this video.",
    "Help me explain this concept in English.",
    "Correct my answer and make it interview-ready.",
    "Give me useful vocabulary from this video.",
]
STARTER_ACTIONS = [
    (
        "Start mock interview",
        "Start a mock interview based on this video. Ask one question at a time.",
    ),
    (
        "Ask me 5 questions",
        "Ask me 5 interview questions about this video, one question at a time.",
    ),
    (
        "Extract interview vocabulary",
        "Extract useful interview vocabulary from this video.",
    ),
    (
        "Help me explain this topic",
        "Help me explain the main topic of this video in English.",
    ),
    (
        "Correct my answer",
        "I want to practice answer improvement. Ask me for an answer, then correct it.",
    ),
]


def render_messages() -> None:
    """Отрисовывает историю сообщений в формате Streamlit chat UI."""
    for item in st.session_state.messages:
        role = "user" if item.get("role") == "user" else "assistant"
        content = str(item.get("content") or "")
        with st.chat_message(role):
            st.markdown(content)


def _render_header(
    selected_video_id: int | None, selected_session_id: int | None
) -> None:
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
    session_label = (
        f"Practice #{session_position}"
        if session_position is not None
        else "No practice session selected"
    )

    with st.container(border=True):
        left_col, right_col = st.columns([4, 1])
        with left_col:
            st.caption("Technical video")
            st.markdown(f"### {video_label}")
        with right_col:
            st.caption("Practice session")
            st.markdown(f"**{session_label}**")


def _render_example_commands() -> None:
    """Показывает короткие примеры команд для interview practice."""
    st.markdown("**Examples:**")
    for command in EXAMPLE_COMMANDS:
        st.markdown(f"- {command}")


def _render_starter_actions(client: BackendAPIClient) -> None:
    """Показывает быстрые стартовые действия для пустой practice session."""
    if st.session_state.messages:
        return

    st.caption("Quick practice starters")
    columns = st.columns(2)
    for index, (label, message) in enumerate(STARTER_ACTIONS):
        with columns[index % 2]:
            if st.button(
                label, key=f"starter_action_{index}", use_container_width=True
            ):
                if send_chat_message(client, message):
                    st.rerun()


def _render_onboarding(client: BackendAPIClient) -> None:
    """Показывает стартовый экран с объяснением сервиса и загрузкой видео."""
    st.caption(APP_TITLE)
    st.title(WELCOME_TITLE)
    st.subheader(WELCOME_SUBTITLE)
    st.info(
        "Выбери техническое видео слева или загрузи новое, чтобы начать interview practice."
    )

    st.markdown(
        "1. Add a technical YouTube video: Python, ML, LLMs, backend, system design, algorithms, databases, DevOps."
    )
    st.markdown("2. Wait while the backend extracts audio and prepares the transcript.")
    st.markdown(
        "3. Discuss the video with an AI coach in English, like in an IT interview."
    )
    st.markdown(
        "4. Get interview-style questions, English corrections, useful phrases, and stronger answers."
    )

    _render_example_commands()

    st.divider()
    render_upload_form(
        client, key_prefix="main", button_label="Загрузить техническое видео"
    )


def _render_video_without_chat(
    client: BackendAPIClient, selected_video_id: int | None
) -> None:
    """Показывает понятное состояние, когда активный чат не выбран."""
    if selected_video_id is None:
        return

    related_sessions = list_sessions_for_video(
        st.session_state.sessions, selected_video_id
    )

    with st.container(border=True):
        if related_sessions:
            st.subheader("This technical video is ready")
            st.caption("Выбери существующую practice session или создай новую.")
            st.markdown("**Interview practice sessions**")

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
            st.subheader("No practice sessions for this video yet")
            st.caption(
                "Создай practice session, чтобы потренироваться объяснять тему видео на английском."
            )

        st.divider()
        _render_example_commands()
        button_label = (
            "New interview practice" if related_sessions else "Start interview practice"
        )
        if st.button(button_label, type="primary", use_container_width=True):
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
        _render_starter_actions(client)
        render_messages()

    prompt = st.chat_input(
        "Answer in English or ask for an interview question...",
        disabled=False,
    )
    if prompt:
        if send_chat_message(client, prompt):
            st.rerun()
