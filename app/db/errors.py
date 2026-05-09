from app.core.errors import AppError


class DatabaseError(AppError):
    """Базовая ошибка слоя данных."""

    module = "db"
    error_code = "db_error"
    status_code = 500


class DatabaseValidationError(DatabaseError):
    """Ошибка валидации входных данных для запросов в БД."""

    error_code = "db_validation_error"
    status_code = 400


class DatabaseOperationError(DatabaseError):
    """Ошибка выполнения SQL-операции."""

    error_code = "db_operation_error"
    status_code = 500
