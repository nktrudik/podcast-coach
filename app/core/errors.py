from collections.abc import Mapping

from app.core.types import JsonValue


class AppError(Exception):
    """Base application error with a consistent API response format."""

    module: str = "core"
    error_code: str = "app_error"
    status_code: int = 500

    def __init__(
        self,
        message: str,
        *,
        details: Mapping[str, JsonValue] | None = None,
        status_code: int | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.details = dict(details) if details else {}
        if status_code is not None:
            self.status_code = status_code

    def to_response(self) -> dict[str, JsonValue]:
        """Return a JSON-serializable error payload."""
        payload: dict[str, JsonValue] = {
            "detail": self.message,
            "error_code": self.error_code,
            "module": self.module,
        }
        if self.details:
            payload["details"] = self.details
        return payload


class ValidationAppError(AppError):
    """User input validation error."""

    module = "core"
    error_code = "validation_error"
    status_code = 400
