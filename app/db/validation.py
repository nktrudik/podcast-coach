from app.db.errors import DatabaseValidationError


def validate_positive_int(value: int, field_name: str) -> int:
    """Проверяет, что значение является положительным целым числом."""
    if not isinstance(value, int):
        raise DatabaseValidationError(f"Поле {field_name} должно быть целым числом")
    if value <= 0:
        raise DatabaseValidationError(f"Поле {field_name} должно быть больше нуля")
    return value


def validate_non_empty_text(value: str, field_name: str) -> str:
    """Проверяет, что строка не пустая после удаления пробелов."""
    if not isinstance(value, str):
        raise DatabaseValidationError(f"Поле {field_name} должно быть строкой")

    normalized_value = value.strip()
    if not normalized_value:
        raise DatabaseValidationError(f"Поле {field_name} не должно быть пустым")
    return normalized_value


def validate_optional_text(value: str | None, field_name: str) -> str | None:
    """Проверяет optional-строку и возвращает нормализованное значение."""
    if value is None:
        return None
    return validate_non_empty_text(value, field_name)


def validate_messages_limit(limit: int | None) -> int | None:
    """Проверяет лимит на количество сообщений в истории."""
    if limit is None:
        return None
    if not isinstance(limit, int):
        raise DatabaseValidationError("Параметр limit должен быть целым числом")
    if limit <= 0:
        raise DatabaseValidationError("Параметр limit должен быть больше нуля")
    if limit > 100:
        raise DatabaseValidationError("Параметр limit не должен превышать 100")
    return limit


def validate_youtube_video_id(youtube_video_id: str) -> str:
    """Проверяет идентификатор YouTube видео."""
    return validate_non_empty_text(youtube_video_id, "youtube_video_id")
