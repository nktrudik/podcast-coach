import time
from collections.abc import Callable

from app.core.logger import get_logger

logger = get_logger(__name__)


def run_with_retry[ResultT](
    operation: Callable[[], ResultT],
    *,
    operation_name: str,
    max_attempts: int,
    delay_seconds: float,
    retry_on: tuple[type[Exception], ...],
) -> ResultT:
    """Retry an operation when one of the configured transient errors is raised."""
    if max_attempts < 1:
        raise ValueError("max_attempts must be greater than zero")

    last_exc: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            return operation()
        except retry_on as exc:
            last_exc = exc
            if attempt < max_attempts:
                logger.warning(
                    "%s transient error on attempt %s/%s: %s",
                    operation_name,
                    attempt,
                    max_attempts,
                    exc,
                )
                if delay_seconds > 0:
                    time.sleep(delay_seconds)

    if last_exc is not None:
        raise last_exc

    raise RuntimeError("Invalid retry execution state")
