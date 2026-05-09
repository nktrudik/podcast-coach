import secrets

from fastapi import Security
from fastapi.security import APIKeyHeader

from app.api.errors import APIAuthorizationError
from app.core.config import Settings, settings
from app.core.logger import get_logger

logger = get_logger(__name__)

_admin_api_key = APIKeyHeader(name="X-Admin-Key", auto_error=False)


def get_settings() -> Settings:
    """Возвращает объект настроек приложения для dependency injection."""
    return settings


def require_admin(key: str | None = Security(_admin_api_key)) -> None:
    """Проверяет административный ключ доступа к защищенным ручкам."""
    if not key or not secrets.compare_digest(key, settings.admin_api_key):
        logger.warning("Попытка доступа к admin-ручке с некорректным ключом")
        raise APIAuthorizationError("Неверный или отсутствующий admin ключ")
