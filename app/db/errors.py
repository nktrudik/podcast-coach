from app.core.errors import AppError


class DatabaseError(AppError):
    """Base data layer error."""

    module = "db"
    error_code = "db_error"
    status_code = 500


class DatabaseValidationError(DatabaseError):
    """Validation error for database operation inputs."""

    error_code = "db_validation_error"
    status_code = 400


class DatabaseOperationError(DatabaseError):
    """SQL operation execution error."""

    error_code = "db_operation_error"
    status_code = 500
