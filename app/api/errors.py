from app.core.errors import AppError


class APIError(AppError):
    """Base API layer error."""

    module = "api"
    error_code = "api_error"
    status_code = 400


class APIAuthorizationError(APIError):
    """Authorization error for protected administrative endpoints."""

    error_code = "api_authorization_error"
    status_code = 401


class APINotFoundError(APIError):
    """Requested entity was not found."""

    error_code = "api_not_found"
    status_code = 404


class APIConflictError(APIError):
    """Request conflicts with the current entity state."""

    error_code = "api_conflict"
    status_code = 409
