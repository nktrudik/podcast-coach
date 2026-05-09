from frontend.api_client import BackendAPIClient
from frontend.config import settings


def get_client() -> BackendAPIClient:
    """Создает API-клиент для обращения к backend."""
    return BackendAPIClient(
        base_url=settings.resolved_backend_base_url,
        timeout_seconds=settings.frontend_request_timeout_seconds,
    )
