import logging
import os
from logging.config import dictConfig

from app.core.config import settings

_is_logging_configured = False


def setup_logging() -> None:
    """Configure application logging for console and file output."""
    global _is_logging_configured
    if _is_logging_configured:
        return

    log_file_dir = os.path.dirname(settings.log_file_path)
    if log_file_dir:
        os.makedirs(log_file_dir, exist_ok=True)

    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
                }
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                },
                "file": {
                    "class": "logging.FileHandler",
                    "filename": settings.log_file_path,
                    "encoding": "utf-8",
                    "formatter": "default",
                },
            },
            "root": {
                "handlers": ["console", "file"],
                "level": settings.log_level,
            },
        }
    )

    _is_logging_configured = True


def get_logger(name: str) -> logging.Logger:
    """Return a named module logger."""
    return logging.getLogger(name)
