from fastapi import APIRouter, HTTPException, status

from app.core.logger import get_logger
from app.db.connection import get_connection

router = APIRouter()
logger = get_logger(__name__)


@router.get("/health")
def health_check() -> dict[str, str]:
    """Проверяет доступность приложения и SQLite."""
    try:
        with get_connection() as conn:
            conn.execute("SELECT 1").fetchone()
    except Exception as exc:
        logger.warning("Health check failed: database unavailable")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "error", "database": "unavailable"},
        ) from exc

    return {"status": "ok", "database": "ok"}
