from app.core.errors import AppError


class ServiceError(AppError):
    """Базовая ошибка сервисного слоя."""

    module = "services"
    error_code = "service_error"
    status_code = 500


class ServiceValidationError(ServiceError):
    """Ошибка валидации входных данных сервиса."""

    error_code = "service_validation_error"
    status_code = 400


class VideoProcessingError(ServiceError):
    """Ошибка обработки видео."""

    error_code = "video_processing_error"
    status_code = 503
