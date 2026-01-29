"""Centralized logging configuration for the AgentStack app."""

from __future__ import annotations

import logging
import os
import sys
from typing import Any, Optional

import structlog
from structlog.typing import Processor

from app.core.config.settings import get_environment

# Environment-driven defaults
DEFAULT_LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
DEFAULT_LOG_FORMAT = os.getenv(
    "LOG_FORMAT", "console").lower()  # console | json


def configure_logging(level: Optional[str | int] = None, fmt: Optional[str] = None) -> None:
    """Configure structlog + stdlib logging.

    Args:
        level: Log level name/number. Falls back to LOG_LEVEL env.
        fmt:   Output format ("console" | "json"). Falls back to LOG_FORMAT env.
    """
    resolved_level = _parse_level(level or DEFAULT_LOG_LEVEL)
    resolved_format = (fmt or DEFAULT_LOG_FORMAT).lower()
    timestamper = structlog.processors.TimeStamper(fmt="iso", utc=True)

    shared_processors = [
        structlog.processors.add_log_level,
        structlog.processors.add_logger_name,
        timestamper,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    renderer: Processor
    if resolved_format == "json":
        renderer = structlog.processors.JSONRenderer()
    else:
        # Default to console-friendly rendering
        renderer = structlog.dev.ConsoleRenderer()

    structlog.configure(
        processors=shared_processors + [renderer],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.make_filtering_bound_logger(resolved_level),
        cache_logger_on_first_use=True,
    )

    logging.basicConfig(
        format="%(message)s",
        level=resolved_level,
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,  # override uvicorn/third-party defaults
    )


def get_logger(name: Optional[str] = None, **context: Any) -> structlog.stdlib.BoundLogger:
    """Return a structlog logger with environment context pre-bound."""
    base = structlog.stdlib.get_logger(name)
    return base.bind(environment=get_environment().value, **context)


def _parse_level(level: str | int) -> int:
    if isinstance(level, int):
        return level
    try:
        # returns int when passed name
        return logging.getLevelName(level.upper())
    except Exception:
        return logging.INFO
