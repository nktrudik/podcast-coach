from app.core.errors import AppError


class ClientError(AppError):
    """Базовая ошибка внешних клиентов."""

    module = "clients"
    error_code = "client_error"
    status_code = 502


class ClientValidationError(ClientError):
    """Ошибка валидации данных перед вызовом внешнего сервиса."""

    error_code = "client_validation_error"
    status_code = 400


class ClientTimeoutError(ClientError):
    """Ошибка таймаута при обращении к внешнему сервису."""

    error_code = "client_timeout_error"
    status_code = 504


class LLMRequestError(ClientError):
    """Ошибка обращения к LLM-сервису."""

    error_code = "llm_request_error"
    status_code = 502


class LLMTimeoutError(ClientTimeoutError):
    """Ошибка таймаута при обращении к LLM-сервису."""

    error_code = "llm_timeout_error"


class STTRequestError(ClientError):
    """Ошибка обращения к STT-сервису."""

    error_code = "stt_request_error"
    status_code = 502


class STTTimeoutError(ClientTimeoutError):
    """Ошибка таймаута при обращении к STT-сервису."""

    error_code = "stt_timeout_error"


class YouTubeDownloadError(ClientError):
    """Ошибка загрузки аудио из YouTube."""

    error_code = "youtube_download_error"
    status_code = 503
