from typing import Any

import streamlit as st


def init_session_state() -> None:
    """Инициализирует состояние интерфейса с безопасными значениями по умолчанию."""
    defaults = {
        "selected_video_id": None,
        "selected_session_id": None,
        "messages": [],
        "videos": [],
        "sessions": [],
        "youtube_url": "",
        "allow_new_video_upload": False,
        "pending_reset_upload_toggle": False,
        "pending_reset_youtube_url": False,
        "pending_reset_input_keys": [],
        "is_video_ready": False,
        "is_state_bootstrapped": False,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def as_positive_int(value: Any) -> int | None:
    """Преобразует значение в положительный int, если это возможно."""
    return value if isinstance(value, int) and value > 0 else None


def normalize_messages(items: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Приводит историю сообщений backend к формату Streamlit chat_message."""
    normalized: list[dict[str, str]] = []
    for item in items:
        role_value = str(item.get("role") or "").strip().lower()
        role = "user" if role_value == "user" else "assistant"
        content = str(item.get("content") or "")
        if not content:
            continue
        normalized.append({"role": role, "content": content})
    return normalized
