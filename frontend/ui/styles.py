import streamlit as st


def apply_app_styles() -> None:
    """Применяет небольшие визуальные правки поверх dark theme Streamlit."""
    st.markdown(
        """
        <style>
        button[data-testid="stExpandSidebarButton"] {
            position: fixed !important;
            left: 16px !important;
            top: 16px !important;
            transform: none !important;
            z-index: 999999 !important;
            margin-left: 0 !important;
            right: auto !important;
        }

        section[data-testid="stSidebar"] {
            min-width: 280px;
            max-width: 320px;
        }

        .block-container {
            max-width: 1040px;
            padding-top: 2rem;
            padding-bottom: 6rem;
        }

        div[data-testid="stChatMessage"] {
            border-radius: 8px;
        }

        h1 {
            letter-spacing: 0;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
