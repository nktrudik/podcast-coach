from app.core.errors import AppError


class ClientError(AppError):
    """Base external client error."""

    module = "clients"
    error_code = "client_error"
    status_code = 502


class ClientValidationError(ClientError):
    """Validation error before calling an external service."""

    error_code = "client_validation_error"
    status_code = 400


class ClientTimeoutError(ClientError):
    """Timeout error while calling an external service."""

    error_code = "client_timeout_error"
    status_code = 504


class LLMRequestError(ClientError):
    """LLM provider request error."""

    error_code = "llm_request_error"
    status_code = 502


class LLMTimeoutError(ClientTimeoutError):
    """Timeout error while calling the LLM provider."""

    error_code = "llm_timeout_error"


class STTRequestError(ClientError):
    """STT provider request error."""

    error_code = "stt_request_error"
    status_code = 502


class STTTimeoutError(ClientTimeoutError):
    """Timeout error while calling the STT provider."""

    error_code = "stt_timeout_error"


class YouTubeDownloadError(ClientError):
    """YouTube audio download error."""

    error_code = "youtube_download_error"
    status_code = 503
