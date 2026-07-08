from app.core.errors import AppError


class ServiceError(AppError):
    """Base service layer error."""

    module = "services"
    error_code = "service_error"
    status_code = 500


class ServiceValidationError(ServiceError):
    """Service input validation error."""

    error_code = "service_validation_error"
    status_code = 400


class VideoProcessingError(ServiceError):
    """Video processing error."""

    error_code = "video_processing_error"
    status_code = 503
