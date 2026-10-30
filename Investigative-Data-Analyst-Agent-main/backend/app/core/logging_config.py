import sys
from loguru import logger
from app.core.config import settings


def setup_logging() -> None:
    """
    Configures the global logger using loguru.
    Removes any default handlers and adds a customized stdout handler.
    Supports backtraces and diagnostics in non-production environments.
    """
    # Remove default handlers to prevent duplicate logs
    logger.remove()

    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    )

    log_level = settings.LOG_LEVEL.upper()

    logger.add(
        sys.stdout,
        format=log_format,
        level=log_level,
        colorize=True,
        backtrace=settings.ENVIRONMENT != "production",
        diagnose=settings.ENVIRONMENT != "production",
    )
    
    logger.info(f"Logging configured at level: {log_level}")
