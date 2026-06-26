from __future__ import annotations

import logging
import logging.config
import sys
from collections.abc import MutableMapping
from typing import Any, TextIO

import structlog

from lewisham_server.settings import LogLevel, Settings

TRACE_LEVEL = 5

SAFE_LOG_FIELDS = frozenset(
    {
        "event",
        "timestamp",
        "level",
        "logger",
        "exception",
        "stack",
        "method",
        "route",
        "status_code",
        "duration_ms",
        "app_version",
        "log_level",
        "log_format",
        "host",
        "port",
        "workers",
        "cache_schedule_ttl_seconds",
        "cache_address_ttl_seconds",
        "cache_negative_ttl_seconds",
        "upstream_base_url",
        "upstream_timeout_seconds",
        "namespace",
        "cache_type",
        "candidate_count",
        "collection_count",
        "next_collection",
        "source_url",
        "fetched_at",
        "endpoint",
        "upstream_path",
        "response_size_bytes",
        "payload_size_bytes",
        "payload_sha256",
        "payload_preview",
        "payload_truncated",
        "error_type",
        "error_message",
    }
)

SENSITIVE_LOG_FIELDS = frozenset(
    {
        "address",
        "address_text",
        "client",
        "client_ip",
        "params",
        "path",
        "path_params",
        "postcode",
        "postcode_or_street",
        "query",
        "query_params",
        "query_string",
        "raw_body",
        "raw_html",
        "raw_payload",
        "search_text",
        "title",
        "uprn",
        "url",
    }
)


class MaxLevelFilter(logging.Filter):
    """Allow records up to and including the configured level."""

    def __init__(self, max_level: int | str) -> None:
        super().__init__()
        self._max_level = _coerce_level(max_level)

    def filter(self, record: logging.LogRecord) -> bool:
        return record.levelno <= self._max_level


class MinLevelFilter(logging.Filter):
    """Allow records at or above the configured level."""

    def __init__(self, min_level: int | str) -> None:
        super().__init__()
        self._min_level = _coerce_level(min_level)

    def filter(self, record: logging.LogRecord) -> bool:
        return record.levelno >= self._min_level


class CurrentStreamHandler(logging.StreamHandler[TextIO]):
    """Write to the current stdout/stderr object at emit time."""

    def __init__(self, stream_name: str) -> None:
        super().__init__(getattr(sys, stream_name))
        self._stream_name = stream_name

    def emit(self, record: logging.LogRecord) -> None:
        self.stream = getattr(sys, self._stream_name)
        super().emit(record)


def configure_logging(settings: Settings) -> None:
    """Configure stdlib logging and structlog with one rendering pipeline."""

    _install_trace_level()
    level = _log_level_value(settings.log_level)
    renderer = (
        structlog.processors.JSONRenderer()
        if settings.log_format == "json"
        else structlog.dev.ConsoleRenderer(colors=False, sort_keys=False)
    )

    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        redact_log_fields,
    ]

    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "filters": {
                "stdout_levels": {
                    "()": "lewisham_server.logging_config.MaxLevelFilter",
                    "max_level": logging.INFO,
                },
                "stderr_levels": {
                    "()": "lewisham_server.logging_config.MinLevelFilter",
                    "min_level": logging.WARNING,
                },
            },
            "formatters": {
                "structured": {
                    "()": structlog.stdlib.ProcessorFormatter,
                    "foreign_pre_chain": shared_processors,
                    "processors": [
                        structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                        renderer,
                    ],
                },
            },
            "handlers": {
                "stdout": {
                    "()": "lewisham_server.logging_config.CurrentStreamHandler",
                    "stream_name": "stdout",
                    "level": TRACE_LEVEL,
                    "filters": ["stdout_levels"],
                    "formatter": "structured",
                },
                "stderr": {
                    "()": "lewisham_server.logging_config.CurrentStreamHandler",
                    "stream_name": "stderr",
                    "level": logging.WARNING,
                    "filters": ["stderr_levels"],
                    "formatter": "structured",
                },
            },
            "root": {
                "handlers": ["stdout", "stderr"],
                "level": level,
            },
            "loggers": {
                "uvicorn": {
                    "handlers": ["stdout", "stderr"],
                    "level": level,
                    "propagate": False,
                },
                "uvicorn.error": {
                    "handlers": ["stdout", "stderr"],
                    "level": level,
                    "propagate": False,
                },
                "uvicorn.access": {
                    "handlers": [],
                    "level": "CRITICAL",
                    "propagate": False,
                },
                "httpx": {
                    "handlers": ["stdout", "stderr"],
                    "level": "WARNING",
                    "propagate": False,
                },
                "httpcore": {
                    "handlers": ["stdout", "stderr"],
                    "level": "WARNING",
                    "propagate": False,
                },
            },
        }
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            redact_log_fields,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def redact_log_fields(
    _: logging.Logger,
    __: str,
    event_dict: MutableMapping[str, Any],
) -> MutableMapping[str, Any]:
    """Drop unapproved structured fields before rendering log output."""

    safe_event: dict[str, Any] = {}
    for key, value in event_dict.items():
        if key.startswith("_") or key in SAFE_LOG_FIELDS:
            safe_event[key] = value
        elif key in SENSITIVE_LOG_FIELDS:
            safe_event[f"{key}_redacted"] = True

    return safe_event


def _install_trace_level() -> None:
    if logging.getLevelName(TRACE_LEVEL) != "TRACE":
        logging.addLevelName(TRACE_LEVEL, "TRACE")


def _log_level_value(level: LogLevel) -> int:
    if level == "trace":
        return TRACE_LEVEL

    return _coerce_level(level.upper())


def _coerce_level(level: int | str) -> int:
    if isinstance(level, int):
        return level

    value = logging.getLevelName(level)
    if not isinstance(value, int):
        raise ValueError(f"Unknown log level: {level!r}")

    return value
