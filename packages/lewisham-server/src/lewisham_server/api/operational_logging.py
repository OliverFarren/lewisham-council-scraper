"""Application-owned logging for outcomes returned by the client library."""

from __future__ import annotations

import logging
from typing import Any

import structlog
from lewisham_client.domain.errors import (
    CollectionScheduleNotFoundError,
    UpstreamScraperChangedError,
    UpstreamUnavailableError,
)

_LOGGER = structlog.get_logger(__name__)
_STDLIB_LOGGER = logging.getLogger(__name__)


def log_address_lookup_completed(*, candidate_count: int) -> None:
    """Record a successful address search returned to the API caller."""
    _LOGGER.info("address_lookup_completed", candidate_count=candidate_count)


def log_schedule_lookup_completed(
    *, collection_count: int, source_url: str, fetched_at: str
) -> None:
    """Record a successful schedule lookup returned to the API caller."""
    _LOGGER.info(
        "schedule_lookup_completed",
        collection_count=collection_count,
        source_url=source_url,
        fetched_at=fetched_at,
    )


def log_upstream_unavailable(error: UpstreamUnavailableError) -> None:
    """Record an upstream failure that the API translates to HTTP 503."""
    _LOGGER.warning("upstream_unavailable", **_diagnostic_fields(error))


def log_contract_drift(error: UpstreamScraperChangedError) -> None:
    """Record an upstream contract failure that the API translates to HTTP 502."""
    _LOGGER.error("upstream_contract_drift", **_diagnostic_fields(error))


def log_parser_schedule_empty(error: CollectionScheduleNotFoundError) -> None:
    """Record a freshly parsed empty schedule without repeating cached misses."""
    if error.diagnostics is None:
        return

    _LOGGER.warning("parser_schedule_empty", **_diagnostic_fields(error))


def _diagnostic_fields(
    error: (
        UpstreamScraperChangedError
        | CollectionScheduleNotFoundError
        | UpstreamUnavailableError
    ),
) -> dict[str, Any]:
    diagnostics = error.diagnostics
    if diagnostics is None:
        return {
            "error_type": type(error).__name__,
            "error_message": str(error),
        }

    fields: dict[str, Any] = {
        "error_type": diagnostics.error_type,
        "error_message": diagnostics.error_message,
    }
    for name in (
        "endpoint",
        "status_code",
        "duration_ms",
        "payload_size_bytes",
        "payload_sha256",
    ):
        value = getattr(diagnostics, name)
        if value is not None:
            fields[name] = value

    if diagnostics.payload_preview is not None and _STDLIB_LOGGER.isEnabledFor(
        logging.DEBUG
    ):
        fields["payload_preview"] = diagnostics.payload_preview
        fields["payload_truncated"] = diagnostics.payload_truncated

    return fields
