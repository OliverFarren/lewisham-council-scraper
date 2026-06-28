"""Test configuration for lewisham-council-client.

Provides configure_test_logging — a minimal structlog JSON logging setup for
tests that assert on log output via pytest's capsys. It mirrors the stdout/stderr
split of the production logging configuration: INFO and below go to stdout,
WARNING and above go to stderr.
"""

from __future__ import annotations

import logging
import logging.config
import sys
from typing import Any

import structlog


class _CurrentStreamHandler(logging.StreamHandler):  # type: ignore[type-arg]
    """Write to the current stdout/stderr object at emit time.

    Standard StreamHandler captures the stream object at construction time, so
    it misses pytest's per-test stdout/stderr redirection. This handler reads
    sys.stdout or sys.stderr dynamically so capsys assertions work correctly.
    """

    def __init__(self, stream_name: str) -> None:
        super().__init__(getattr(sys, stream_name))
        self._stream_name = stream_name

    def emit(self, record: logging.LogRecord) -> None:
        self.stream = getattr(sys, self._stream_name)
        super().emit(record)


class _MaxLevelFilter(logging.Filter):
    """Allow log records up to and including max_level."""

    def __init__(self, max_level: int) -> None:
        super().__init__()
        self._max_level = max_level

    def filter(self, record: logging.LogRecord) -> bool:
        return record.levelno <= self._max_level


def configure_test_logging(level: str = "debug") -> None:
    """Configure structlog for JSON output in tests.

    Routes INFO and below to stdout and WARNING and above to stderr, matching
    the split used in production so that capsys assertions on .out and .err
    work correctly.

    Call at the start of any test that asserts on structured log output. Sets
    cache_logger_on_first_use=False so repeated calls during a test session take
    effect immediately.
    """
    numeric_level = getattr(logging, level.upper())

    shared_processors: list[Any] = [
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="%Y-%m-%dT%H:%M:%SZ", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "json": {
                    "()": structlog.stdlib.ProcessorFormatter,
                    "foreign_pre_chain": shared_processors,
                    "processors": [
                        structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                        structlog.processors.JSONRenderer(),
                    ],
                },
            },
            "handlers": {
                "stdout": {
                    "()": f"{__name__}._CurrentStreamHandler",
                    "stream_name": "stdout",
                    "level": numeric_level,
                    "filters": ["stdout_max"],
                    "formatter": "json",
                },
                "stderr": {
                    "()": f"{__name__}._CurrentStreamHandler",
                    "stream_name": "stderr",
                    "level": logging.WARNING,
                    "formatter": "json",
                },
            },
            "filters": {
                "stdout_max": {
                    "()": f"{__name__}._MaxLevelFilter",
                    "max_level": logging.INFO,
                },
            },
            "root": {
                "handlers": ["stdout", "stderr"],
                "level": numeric_level,
            },
        }
    )

    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="%Y-%m-%dT%H:%M:%SZ", utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=False,
    )
