"""
Application-wide logging setup.

Configures the root logger with a rotating file handler plus a console
handler. The log level and rotation policy are fully controlled via
Settings (i.e. environment variables) -- nothing here is hardcoded.
"""

import logging
from logging.handlers import RotatingFileHandler

from app.core.config import Settings, get_settings
from app.utils.constants import LOG_DATE_FORMAT, LOG_FORMAT

_configured = False


def setup_logging(settings: Settings | None = None) -> None:
    """
    Configure the root logger with a console handler and a rotating file
    handler, sized and leveled according to Settings. Safe to call more than
    once -- subsequent calls are no-ops.
    """
    global _configured
    if _configured:
        return

    settings = settings or get_settings()
    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    formatter = logging.Formatter(fmt=LOG_FORMAT, datefmt=LOG_DATE_FORMAT)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    file_handler = RotatingFileHandler(
        filename=settings.log_file_path,
        maxBytes=settings.LOG_MAX_BYTES,
        backupCount=settings.LOG_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers = [console_handler, file_handler]

    _configured = True


def get_logger(name: str) -> logging.Logger:
    """Return a module-scoped logger. Call `setup_logging()` once at startup first."""
    return logging.getLogger(name)
