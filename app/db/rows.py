from collections.abc import Mapping

from app.core.types import DatabaseRecord, DatabaseValue
from app.db.errors import DatabaseOperationError


def to_database_record(row: Mapping[str, object]) -> DatabaseRecord:
    """Convert a psycopg row into a narrow JSON-friendly record."""
    return {key: _to_database_value(value) for key, value in row.items()}


def _to_database_value(value: object) -> DatabaseValue:
    """Normalize PostgreSQL scalar values used by the API."""
    if value is None or isinstance(value, str | int | float | bool):
        return value
    return str(value)


def required_int(row: Mapping[str, object], field_name: str, entity_name: str) -> int:
    """Extract a required integer field from a raw database row."""
    value = row.get(field_name)
    if isinstance(value, bool):
        raise DatabaseOperationError(
            f"The {entity_name} row has an invalid {field_name}"
        )
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    raise DatabaseOperationError(f"The {entity_name} row has an invalid {field_name}")
