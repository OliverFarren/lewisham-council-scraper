import json
import logging
from datetime import date

import pytest

from lewisham_client.clients.lewisham import LewishamParser
from lewisham_client.domain.errors import (
    CollectionScheduleNotFoundError,
    UpstreamScraperChangedError,
)

_PARSER_LOGGER = "lewisham_client.clients.lewisham.parser"


def encode_html(fragment: str) -> str:
    return json.dumps(fragment)


def _event_record(
    caplog: pytest.LogCaptureFixture,
    event: str,
) -> logging.LogRecord:
    return next(
        record
        for record in caplog.records
        if record.name == _PARSER_LOGGER and record.getMessage() == event
    )


# Reference date for tests: Friday 2026-06-26.
# Next Thursday from Friday: (3 - 4) % 7 = 6 days → 2026-07-02.
# Next Monday from Friday: (0 - 4) % 7 = 3 days → 2026-06-29.
_REFERENCE_DATE = date(2026, 6, 26)


def test_parser_extracts_residential_schedule() -> None:
    parser = LewishamParser()
    raw_body = encode_html(
        """
        <h2>When your bins are collected:</h2>
        <strong>Food waste</strong>&nbsp;is collected
        <span class="RoundsTransform">WEEKLY</span> on Thursday.
        <br><br>
        <strong>Recycling</strong>&nbsp;is collected
        <span class="RoundsTransform">WEEKLY</span> on Thursday.
        <br><br>
        <strong>Refuse</strong>&nbsp;is collected
        <span class="RoundsTransform">FORTNIGHTLY</span> on Thursday.
        Your next collection date is 02/07/2026.
        """
    )

    schedule = parser.parse_collection_schedule(
        raw_body, reference_date=_REFERENCE_DATE
    )

    assert [entry.waste_type for entry in schedule.collections] == [
        "Food waste",
        "Recycling",
        "Refuse",
    ]
    assert [entry.frequency for entry in schedule.collections] == [
        "WEEKLY",
        "WEEKLY",
        "FORTNIGHTLY",
    ]
    assert {entry.day for entry in schedule.collections} == {"Thursday"}


def test_parser_attaches_published_date_to_fortnightly_entry_not_weekly() -> None:
    """The published date follows Refuse in the HTML and belongs only to that entry."""
    parser = LewishamParser()
    raw_body = encode_html(
        """
        <strong>Recycling</strong>&nbsp;is collected
        <span class="RoundsTransform">WEEKLY</span> on Friday.
        <br><br>
        <strong>Refuse</strong>&nbsp;is collected
        <span class="RoundsTransform">FORTNIGHTLY</span> on Friday.
        Your next collection date is 10/07/2026.
        """
    )

    schedule = parser.parse_collection_schedule(
        raw_body, reference_date=_REFERENCE_DATE
    )

    recycling, refuse = schedule.collections
    assert recycling.next_collection == date(2026, 6, 26)  # derived: same-day Friday
    assert recycling.next_collection_basis == "weekday_derived"
    assert refuse.next_collection == date(2026, 7, 10)
    assert refuse.next_collection_basis == "published"


def test_parser_derives_next_weekday_for_weekly_entries() -> None:
    parser = LewishamParser()
    raw_body = encode_html(
        """
        <strong>Food waste</strong>&nbsp;is collected
        <span class="RoundsTransform">WEEKLY</span> on Thursday.
        """
    )

    schedule = parser.parse_collection_schedule(
        raw_body, reference_date=_REFERENCE_DATE
    )

    entry = schedule.collections[0]
    assert entry.next_collection == date(2026, 7, 2)
    assert entry.next_collection_basis == "weekday_derived"


def test_parser_returns_null_for_fortnightly_without_published_date() -> None:
    parser = LewishamParser()
    raw_body = encode_html(
        """
        <strong>Refuse</strong>&nbsp;is collected
        <span class="RoundsTransform">FORTNIGHTLY</span> on Thursday.
        """
    )

    schedule = parser.parse_collection_schedule(
        raw_body, reference_date=_REFERENCE_DATE
    )

    entry = schedule.collections[0]
    assert entry.next_collection is None
    assert entry.next_collection_basis is None


def test_parser_detects_empty_schedule() -> None:
    parser = LewishamParser()
    raw_body = encode_html(
        """
        <p>
          If you think the above is incorrect or is missing please notify us
        </p>
        """
    )

    with pytest.raises(CollectionScheduleNotFoundError):
        parser.parse_collection_schedule(raw_body, reference_date=_REFERENCE_DATE)


def test_parser_allows_partial_civic_schedule() -> None:
    parser = LewishamParser()
    raw_body = encode_html(
        """
        <strong>Recycling</strong>&nbsp;is collected
        <span class="RoundsTransform">WEEKLY</span> on Monday.
        """
    )

    schedule = parser.parse_collection_schedule(
        raw_body, reference_date=_REFERENCE_DATE
    )

    assert len(schedule.collections) == 1
    entry = schedule.collections[0]
    assert entry.waste_type == "Recycling"
    assert entry.next_collection == date(2026, 6, 29)  # next Monday from Friday
    assert entry.next_collection_basis == "weekday_derived"


def test_parser_rejects_unrecognised_frequency() -> None:
    parser = LewishamParser()
    raw_body = encode_html(
        """
        <strong>Refuse</strong>&nbsp;is collected
        <span class="RoundsTransform">4-WEEKLY</span> on Thursday.
        """
    )

    with pytest.raises(UpstreamScraperChangedError):
        parser.parse_collection_schedule(raw_body, reference_date=_REFERENCE_DATE)


def test_parser_rejects_malformed_json() -> None:
    parser = LewishamParser()

    with pytest.raises(UpstreamScraperChangedError):
        parser.parse_collection_schedule("{not-json", reference_date=_REFERENCE_DATE)


def test_parser_logs_contract_drift_without_raw_payload_by_default(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.DEBUG, logger=_PARSER_LOGGER)
    parser = LewishamParser()
    raw_body = "{not-json SECRET-UPSTREAM-PAYLOAD"

    with pytest.raises(UpstreamScraperChangedError):
        parser.parse_collection_schedule(raw_body, reference_date=_REFERENCE_DATE)

    event = _event_record(caplog, "parser_contract_drift")

    assert event.levelno == logging.DEBUG
    assert event.payload_size_bytes == len(raw_body.encode("utf-8"))
    assert event.payload_sha256 is not None
    assert not hasattr(event, "payload_preview")
    assert "SECRET-UPSTREAM-PAYLOAD" not in repr(event.__dict__)


def test_parser_logs_raw_preview_only_with_debug_and_explicit_opt_in(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.DEBUG, logger=_PARSER_LOGGER)
    parser = LewishamParser(include_raw_upstream=True, raw_upstream_max_chars=10)
    raw_body = "{not-json SECRET-UPSTREAM-PAYLOAD"

    with pytest.raises(UpstreamScraperChangedError):
        parser.parse_collection_schedule(raw_body, reference_date=_REFERENCE_DATE)

    event = _event_record(caplog, "parser_contract_drift")

    assert event.payload_preview == raw_body[:10]
    assert event.payload_truncated is True


def test_parser_emits_no_event_when_debug_is_disabled(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO, logger=_PARSER_LOGGER)
    parser = LewishamParser(include_raw_upstream=True, raw_upstream_max_chars=10)
    raw_body = "{not-json SECRET-UPSTREAM-PAYLOAD"

    with pytest.raises(UpstreamScraperChangedError):
        parser.parse_collection_schedule(raw_body, reference_date=_REFERENCE_DATE)

    assert all(
        record.name != _PARSER_LOGGER or record.getMessage() != "parser_contract_drift"
        for record in caplog.records
    )
    assert "SECRET-UPSTREAM-PAYLOAD" not in caplog.text


def test_parser_rejects_malformed_date_phrase() -> None:
    parser = LewishamParser()
    raw_body = encode_html(
        """
        <strong>Refuse</strong>&nbsp;is collected
        <span class="RoundsTransform">FORTNIGHTLY</span> on Thursday.
        Your next collection date is someday soon.
        """
    )

    with pytest.raises(UpstreamScraperChangedError):
        parser.parse_collection_schedule(raw_body, reference_date=_REFERENCE_DATE)


def test_parser_rejects_invalid_calendar_date() -> None:
    parser = LewishamParser()
    raw_body = encode_html(
        """
        <strong>Refuse</strong>&nbsp;is collected
        <span class="RoundsTransform">FORTNIGHTLY</span> on Thursday.
        Your next collection date is 32/13/2026.
        """
    )

    with pytest.raises(UpstreamScraperChangedError):
        parser.parse_collection_schedule(raw_body, reference_date=_REFERENCE_DATE)


def test_parser_attaches_diagnostics_without_preview_by_default() -> None:
    """diagnostics.payload_sha256/size are always populated; preview is opt-in."""
    parser = LewishamParser()
    raw_body = "{not-json SECRET-UPSTREAM-PAYLOAD"

    with pytest.raises(UpstreamScraperChangedError) as exc_info:
        parser.parse_collection_schedule(raw_body, reference_date=_REFERENCE_DATE)

    diagnostics = exc_info.value.diagnostics
    assert diagnostics is not None
    assert diagnostics.error_type == "UpstreamScraperChangedError"
    assert diagnostics.source == "parser"
    assert diagnostics.payload_size_bytes == len(raw_body.encode("utf-8"))
    assert diagnostics.payload_sha256 is not None
    assert diagnostics.payload_preview is None


def test_parser_attaches_preview_diagnostics_when_opted_in_no_debug() -> None:
    """Unlike logging, the returned diagnostics preview needs no DEBUG level."""
    parser = LewishamParser(include_raw_upstream=True, raw_upstream_max_chars=10)
    raw_body = "{not-json SECRET-UPSTREAM-PAYLOAD"

    with pytest.raises(UpstreamScraperChangedError) as exc_info:
        parser.parse_collection_schedule(raw_body, reference_date=_REFERENCE_DATE)

    diagnostics = exc_info.value.diagnostics
    assert diagnostics is not None
    assert diagnostics.payload_preview == raw_body[:10]
    assert diagnostics.payload_truncated is True


def test_parser_attaches_diagnostics_to_empty_schedule_error() -> None:
    """The zero-entries CollectionScheduleNotFoundError also carries diagnostics."""
    parser = LewishamParser()
    raw_body = encode_html(
        """
        <p>
          If you think the above is incorrect or is missing please notify us
        </p>
        """
    )

    with pytest.raises(CollectionScheduleNotFoundError) as exc_info:
        parser.parse_collection_schedule(raw_body, reference_date=_REFERENCE_DATE)

    diagnostics = exc_info.value.diagnostics
    assert diagnostics is not None
    assert diagnostics.error_type == "CollectionScheduleNotFoundError"
    assert diagnostics.source == "parser"
    assert diagnostics.payload_sha256 is not None


def test_parser_logs_empty_schedule_as_debug_not_contract_drift(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A genuinely empty schedule remains diagnostic inside the library."""
    caplog.set_level(logging.DEBUG, logger=_PARSER_LOGGER)
    parser = LewishamParser()
    raw_body = encode_html(
        """
        <p>
          If you think the above is incorrect or is missing please notify us
        </p>
        """
    )

    with pytest.raises(CollectionScheduleNotFoundError):
        parser.parse_collection_schedule(raw_body, reference_date=_REFERENCE_DATE)

    assert all(
        record.name != _PARSER_LOGGER or record.getMessage() != "parser_contract_drift"
        for record in caplog.records
    )
    empty_event = _event_record(caplog, "parser_schedule_empty")
    assert empty_event.levelno == logging.DEBUG
    assert all(record.levelno < logging.WARNING for record in caplog.records)


def test_parser_normalises_non_breaking_spaces_and_frequency_case() -> None:
    parser = LewishamParser()
    raw_body = encode_html(
        """
        <strong>Food\xa0waste</strong>&nbsp;is collected
        <span class="RoundsTransform">fortnightly</span> on Thursday.
        """
    )

    schedule = parser.parse_collection_schedule(
        raw_body, reference_date=_REFERENCE_DATE
    )

    assert schedule.collections[0].waste_type == "Food waste"
    assert schedule.collections[0].frequency == "FORTNIGHTLY"
    assert schedule.collections[0].next_collection is None
