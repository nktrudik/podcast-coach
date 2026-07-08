import secrets

from fastapi import Security
from fastapi.security import APIKeyHeader

from app.api.errors import APIAuthorizationError
from app.core.config import Settings, settings
from app.core.logger import get_logger

logger = get_logger(__name__)

_admin_api_key = APIKeyHeader(name="X-Admin-Key", auto_error=False)


def get_settings() -> Settings:
    """Return application settings for dependency injection."""
    return settings


def require_admin(key: str | None = Security(_admin_api_key)) -> None:
    """Validate the administrative API key for protected endpoints."""
    if not key or not secrets.compare_digest(key, settings.admin_api_key):
        logger.warning("Admin endpoint access denied because the key is invalid")
        raise APIAuthorizationError("Missing or invalid admin key")
