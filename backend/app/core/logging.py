"""
Structured logging configuration using structlog.
Every log event includes a job_id where available.
"""

from __future__ import annotations

import logging
from typing import Any

import structlog


def configure_logging(debug: bool = False) -> None:
    """Call once at application startup."""
    level = logging.DEBUG if debug else logging.INFO

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer() if debug else structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = "patchpilot") -> Any:
    return structlog.get_logger(name)
