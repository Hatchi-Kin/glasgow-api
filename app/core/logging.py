import logging
import sys

from app.core.config import settings


def setup_logging() -> None:
    """Configure application logging."""

    # Configure root logger
    logging.basicConfig(
        level=logging.DEBUG if settings.debug else logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    # Set specific logger levels
    loggers_config = {
        "uvicorn": logging.INFO,
        "uvicorn.access": logging.INFO,
        "fastapi": logging.INFO,
        "app": logging.DEBUG if settings.debug else logging.INFO,
    }

    for logger_name, level in loggers_config.items():
        logging.getLogger(logger_name).setLevel(level)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for the given name."""
    return logging.getLogger(f"app.{name}")
