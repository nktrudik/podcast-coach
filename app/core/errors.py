from typing import Any


class AppError(Exception):
    """Базовая ошибка приложения с единым форматом для API-ответа."""

    module: str = "core"
    error_code: str = "app_error"
    status_code: int = 500

    def __init__(
        self,
        message: str,
        *,
        details: dict[str, Any] | None = None,
        status_code: int | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}
        if status_code is not None:
            self.status_code = status_code

    def to_response(self) -> dict[str, Any]:
        """Возвращает структуру ошибки для JSON-ответа."""
        payload: dict[str, Any] = {
            "detail": self.message,
            "error_code": self.error_code,
            "module": self.module,
        }
        if self.details:
            payload["details"] = self.details
        return payload


class ValidationAppError(AppError):
    """Ошибка валидации пользовательского ввода."""

    module = "core"
    error_code = "validation_error"
    status_code = 400
