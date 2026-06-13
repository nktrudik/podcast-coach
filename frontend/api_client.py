from dataclasses import dataclass
from typing import Any

import requests


@dataclass(slots=True)
class BackendAPIError(Exception):
    """Ошибка взаимодействия Streamlit frontend с backend API."""

    message: str
    status_code: int | None = None
    error_code: str | None = None
    details: dict[str, Any] | None = None

    def __str__(self) -> str:
        return self.message


class BackendAPIClient:
    """Минимальный HTTP-клиент для работы с backend API."""

    def __init__(self, base_url: str, timeout_seconds: float = 60.0) -> None:
        if not isinstance(base_url, str) or not base_url.strip():
            raise ValueError("base_url должен быть непустой строкой")

        self.base_url = base_url.strip().rstrip("/")
        self.timeout_seconds = timeout_seconds

    def _request(
        self,
        method: str,
        path: str,
        *,
        json_payload: dict[str, Any] | None = None,
    ) -> Any:
        url = f"{self.base_url}{path}"

        try:
            response = requests.request(
                method=method,
                url=url,
                json=json_payload,
                timeout=self.timeout_seconds,
            )
        except requests.Timeout as exc:
            raise BackendAPIError("Превышено время ожидания ответа backend") from exc
        except requests.RequestException as exc:
            raise BackendAPIError("Не удалось подключиться к backend") from exc

        if response.status_code >= 400:
            self._raise_api_error(response)

        if response.status_code == 204:
            return None

        try:
            return response.json()
        except ValueError as exc:
            raise BackendAPIError(
                "Backend вернул ответ в некорректном формате"
            ) from exc

    def _raise_api_error(self, response: requests.Response) -> None:
        message = f"Backend вернул ошибку {response.status_code}"
        error_code: str | None = None
        details: dict[str, Any] | None = None

        try:
            payload = response.json()
        except ValueError:
            payload = None

        if isinstance(payload, dict):
            detail_value = payload.get("detail")
            if isinstance(detail_value, str) and detail_value.strip():
                message = detail_value
            elif detail_value is not None:
                message = str(detail_value)

            payload_error_code = payload.get("error_code")
            if isinstance(payload_error_code, str) and payload_error_code.strip():
                error_code = payload_error_code

            payload_details = payload.get("details")
            if isinstance(payload_details, dict):
                details = payload_details

        raise BackendAPIError(
            message=message,
            status_code=response.status_code,
            error_code=error_code,
            details=details,
        )

    def upload_video(self, youtube_url: str) -> int:
        """Запускает обработку YouTube-видео и возвращает id видео."""
        payload = self._request(
            "POST", "/videos", json_payload={"youtube_url": youtube_url}
        )
        video_id = payload.get("video_id") if isinstance(payload, dict) else None
        if not isinstance(video_id, int):
            raise BackendAPIError("Backend вернул некорректный video_id")
        return video_id

    def list_videos(self) -> list[dict[str, Any]]:
        """Возвращает список загруженных видео."""
        payload = self._request("GET", "/videos")
        if not isinstance(payload, list):
            raise BackendAPIError("Backend вернул некорректный список видео")
        return [item for item in payload if isinstance(item, dict)]

    def get_video(self, video_id: int) -> dict[str, Any]:
        """Возвращает данные конкретного видео по id."""
        payload = self._request("GET", f"/videos/{video_id}")
        if not isinstance(payload, dict):
            raise BackendAPIError("Backend вернул некорректные данные видео")
        return payload

    def start_chat(self, video_id: int) -> int:
        """Создает новую чат-сессию и возвращает session_id."""
        payload = self._request(
            "POST", "/chat/start", json_payload={"video_id": video_id}
        )
        session_id = payload.get("session_id") if isinstance(payload, dict) else None
        if not isinstance(session_id, int):
            raise BackendAPIError("Backend вернул некорректный session_id")
        return session_id

    def list_sessions(self) -> list[dict[str, Any]]:
        """Возвращает список доступных чат-сессий."""
        payload = self._request("GET", "/chat/sessions")
        if not isinstance(payload, list):
            raise BackendAPIError("Backend вернул некорректный список сессий")
        return [item for item in payload if isinstance(item, dict)]

    def get_session_messages(self, session_id: int) -> list[dict[str, Any]]:
        """Возвращает историю сообщений выбранной сессии."""
        payload = self._request("GET", f"/chat/sessions/{session_id}/messages")
        if not isinstance(payload, list):
            raise BackendAPIError("Backend вернул некорректную историю сообщений")
        return [item for item in payload if isinstance(item, dict)]

    def send_message(self, session_id: int, message: str) -> str:
        """Отправляет сообщение и возвращает ответ ассистента."""
        payload = self._request(
            "POST",
            "/chat/message",
            json_payload={"session_id": session_id, "message": message},
        )
        answer = payload.get("answer") if isinstance(payload, dict) else None
        if not isinstance(answer, str):
            raise BackendAPIError("Backend вернул некорректный ответ ассистента")
        return answer
