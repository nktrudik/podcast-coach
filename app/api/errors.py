from app.core.errors import AppError


class APIError(AppError):
    """Базовая ошибка API-слоя."""

    module = "api"
    error_code = "api_error"
    status_code = 400


class APIAuthorizationError(APIError):
    """Ошибка авторизации в административных ручках."""

    error_code = "api_authorization_error"
    status_code = 401


class APINotFoundError(APIError):
    """Запрошенная сущность не найдена."""

    error_code = "api_not_found"
    status_code = 404


class APIConflictError(APIError):
    """Конфликт состояния запроса."""

    error_code = "api_conflict"
    status_code = 409
