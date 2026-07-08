from app.db.errors import DatabaseValidationError


def validate_positive_int(value: int, field_name: str) -> int:
    """Validate that a value is a positive integer."""
    if not isinstance(value, int):
        raise DatabaseValidationError(f"Field {field_name} must be an integer")
    if value <= 0:
        raise DatabaseValidationError(f"Field {field_name} must be greater than zero")
    return value


def validate_non_empty_text(value: str, field_name: str) -> str:
    """Validate that a string is not empty after trimming whitespace."""
    if not isinstance(value, str):
        raise DatabaseValidationError(f"Field {field_name} must be a string")

    normalized_value = value.strip()
    if not normalized_value:
        raise DatabaseValidationError(f"Field {field_name} must not be empty")
    return normalized_value


def validate_optional_text(value: str | None, field_name: str) -> str | None:
    """Validate an optional string and return a normalized value."""
    if value is None:
        return None
    return validate_non_empty_text(value, field_name)


def validate_messages_limit(limit: int | None) -> int | None:
    """Validate the message history limit."""
    if limit is None:
        return None
    if not isinstance(limit, int):
        raise DatabaseValidationError("Parameter limit must be an integer")
    if limit <= 0:
        raise DatabaseValidationError("Parameter limit must be greater than zero")
    if limit > 100:
        raise DatabaseValidationError("Parameter limit must not exceed 100")
    return limit


def validate_youtube_video_id(youtube_video_id: str) -> str:
    """Validate a YouTube video identifier."""
    return validate_non_empty_text(youtube_video_id, "youtube_video_id")
