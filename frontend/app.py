import streamlit as st
from frontend.ui.actions import bootstrap_state
from frontend.ui.components import render_chat_panel, render_sidebar
from frontend.ui.dependencies import get_client
from frontend.ui.state import init_session_state
from frontend.ui.styles import apply_app_styles


st.set_page_config(
    page_title="English Interview Coach for IT",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded",
)


def main() -> None:
    """Точка входа Streamlit-приложения."""
    init_session_state()
    try:
        apply_app_styles()
        client = get_client()
        bootstrap_state(client)

        render_sidebar(client)
        render_chat_panel(client)
    except Exception:
        # Не показываем пользователю технические детали, лог оставит traceback в терминале.
        st.error(
            "Произошла внутренняя ошибка интерфейса. Обнови страницу и попробуй снова."
        )
        st.stop()


if __name__ == "__main__":
    main()
