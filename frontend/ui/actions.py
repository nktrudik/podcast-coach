import streamlit as st

from frontend.api_client import BackendAPIClient, BackendAPIError
from frontend.ui.catalog import list_sessions_for_video, resolve_selection
from frontend.ui.state import as_positive_int, normalize_messages


def request_upload_toggle_reset() -> None:
    """Планирует безопасный сброс чекбокса загрузки перед следующим рендером виджета."""
    st.session_state.pending_reset_upload_toggle = True


def request_youtube_url_reset() -> None:
    """Планирует безопасный сброс поля youtube_url перед следующим рендером виджета."""
    st.session_state.pending_reset_youtube_url = True


def request_input_reset(state_key: str) -> None:
    """Планирует безопасный сброс input-виджета перед следующим рендером."""
    pending_keys = st.session_state.get("pending_reset_input_keys", [])
    if not isinstance(pending_keys, list):
        pending_keys = []
    if state_key not in pending_keys:
        pending_keys.append(state_key)
    st.session_state.pending_reset_input_keys = pending_keys


def sync_state_from_backend(
    client: BackendAPIClient,
    *,
    preferred_video_id: int | None = None,
    preferred_session_id: int | None = None,
    auto_select_video: bool = True,
    auto_select_session: bool = True,
) -> None:
    """Синхронизирует данные интерфейса с backend API."""
    current_video_id = as_positive_int(st.session_state.selected_video_id)
    current_session_id = as_positive_int(st.session_state.selected_session_id)

    resolved_video_id = preferred_video_id if preferred_video_id is not None else current_video_id
    resolved_session_id = preferred_session_id if preferred_session_id is not None else current_session_id

    videos = client.list_videos()
    sessions = client.list_sessions()

    selected_video_id, selected_session_id = resolve_selection(
        videos,
        sessions,
        resolved_video_id,
        resolved_session_id,
        auto_select_video=auto_select_video,
        auto_select_session=auto_select_session,
    )

    if selected_session_id is not None:
        messages = normalize_messages(client.get_session_messages(selected_session_id))
    else:
        messages = []

    st.session_state.videos = videos
    st.session_state.sessions = sessions
    st.session_state.selected_video_id = selected_video_id
    st.session_state.selected_session_id = selected_session_id
    st.session_state.messages = messages
    st.session_state.is_video_ready = selected_session_id is not None


def bootstrap_state(client: BackendAPIClient) -> None:
    """Первичная загрузка данных из backend после refresh страницы."""
    if st.session_state.is_state_bootstrapped:
        return

    try:
        with st.spinner("Loading technical videos and practice sessions..."):
            sync_state_from_backend(
                client,
                preferred_video_id=None,
                preferred_session_id=None,
                auto_select_video=False,
                auto_select_session=False,
            )
    except BackendAPIError as exc:
        st.error(str(exc))
        return

    st.session_state.is_state_bootstrapped = True


def refresh_state(client: BackendAPIClient) -> bool:
    """Принудительно обновляет данные видео/чатов из backend."""
    try:
        sync_state_from_backend(
            client,
            auto_select_video=as_positive_int(st.session_state.selected_video_id) is not None,
            auto_select_session=as_positive_int(st.session_state.selected_session_id) is not None,
        )
    except BackendAPIError as exc:
        st.error(str(exc))
        return False
    return True


def select_video(client: BackendAPIClient, video_id: int) -> bool:
    """Выбирает видео и показывает список его чат-сессий без автоперехода в чат."""
    try:
        st.session_state.selected_session_id = None
        sync_state_from_backend(
            client,
            preferred_video_id=video_id,
            preferred_session_id=None,
            auto_select_session=False,
        )
    except BackendAPIError as exc:
        st.error(str(exc))
        return False

    request_upload_toggle_reset()
    return True


def select_session(client: BackendAPIClient, session_id: int) -> bool:
    """Выбирает чат-сессию и загружает ее историю."""
    try:
        sync_state_from_backend(client, preferred_session_id=session_id)
    except BackendAPIError as exc:
        st.error(str(exc))
        return False

    request_upload_toggle_reset()
    return True


def create_session_for_video(client: BackendAPIClient, video_id: int) -> bool:
    """Создает новую чат-сессию для указанного видео и делает ее активной."""
    try:
        session_id = client.start_chat(video_id)
        sync_state_from_backend(
            client,
            preferred_video_id=video_id,
            preferred_session_id=session_id,
        )
    except BackendAPIError as exc:
        st.error(str(exc))
        return False

    st.session_state.is_state_bootstrapped = True
    request_upload_toggle_reset()
    return True


def process_video_upload(client: BackendAPIClient, *, state_key: str = "youtube_url") -> bool:
    """Обрабатывает YouTube URL, создает или выбирает чат и открывает его."""
    youtube_url = str(st.session_state.get(state_key) or "").strip()
    if not youtube_url:
        st.error("Укажи ссылку на техническое YouTube-видео перед обработкой")
        return False

    try:
        with st.spinner("Processing technical video..."):
            video_id = client.upload_video(youtube_url)
            sessions = client.list_sessions()
            existing_sessions = list_sessions_for_video(sessions, video_id)

            if existing_sessions:
                st.session_state.selected_session_id = None
                sync_state_from_backend(
                    client,
                    preferred_video_id=video_id,
                    preferred_session_id=None,
                    auto_select_session=False,
                )
            else:
                session_id = client.start_chat(video_id)
                sync_state_from_backend(
                    client,
                    preferred_video_id=video_id,
                    preferred_session_id=session_id,
                )
    except BackendAPIError as exc:
        st.error(str(exc))
        return False

    st.session_state.is_state_bootstrapped = True
    request_input_reset(state_key)
    if state_key == "youtube_url":
        request_youtube_url_reset()
    request_upload_toggle_reset()
    return True


def send_chat_message(client: BackendAPIClient, message: str) -> bool:
    """Отправляет сообщение ассистенту и перезагружает историю активной сессии."""
    session_id = as_positive_int(st.session_state.selected_session_id)
    video_id = as_positive_int(st.session_state.selected_video_id)
    if session_id is None:
        if video_id is None:
            st.error("Сначала выбери или загрузи техническое видео")
            return False
        try:
            session_id = client.start_chat(video_id)
            sync_state_from_backend(
                client,
                preferred_video_id=video_id,
                preferred_session_id=session_id,
            )
        except BackendAPIError as exc:
            st.error(str(exc))
            return False

    normalized_message = message.strip()
    if not normalized_message:
        return False

    try:
        with st.spinner("Coach is preparing feedback..."):
            client.send_message(session_id, normalized_message)
            st.session_state.messages = normalize_messages(client.get_session_messages(session_id))
    except BackendAPIError as exc:
        st.error(str(exc))
        return False

    return True
