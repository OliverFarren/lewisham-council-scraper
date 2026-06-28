import json
from datetime import date

import pytest

from lewisham_server.clients.lewisham import LewishamParser
from lewisham_server.domain.errors import (
    CollectionScheduleNotFoundError,
    UpstreamScraperChangedError,
)
from lewisham_server.logging_config import configure_logging
from lewisham_server.settings import Settings


def encode_html(fragment: str) -> str:
    return json.dumps(fragment)


def json_events(output: str) -> list[dict[str, object]]:
    return [json.loads(line) for line in output.splitlines()]


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

    schedule = parser.parse_collection_schedule(raw_body, reference_date=_REFERENCE_DATE)

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

    schedule = parser.parse_collection_schedule(raw_body, reference_date=_REFERENCE_DATE)

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

    schedule = parser.parse_collection_schedule(raw_body, reference_date=_REFERENCE_DATE)

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

    schedule = parser.parse_collection_schedule(raw_body, reference_date=_REFERENCE_DATE)

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

    schedule = parser.parse_collection_schedule(raw_body, reference_date=_REFERENCE_DATE)

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


def test_parser_logs_contract_drift_without_raw_payload_by_default(capsys) -> None:
    configure_logging(Settings(log_format="json", log_level="debug"))
    parser = LewishamParser()
    raw_body = "{not-json SECRET-UPSTREAM-PAYLOAD"

    with pytest.raises(UpstreamScraperChangedError):
        parser.parse_collection_schedule(raw_body, reference_date=_REFERENCE_DATE)

    captured = capsys.readouterr()
    event = json_events(captured.err)[0]

    assert event["event"] == "parser_contract_drift"
    assert event["payload_size_bytes"] == len(raw_body.encode("utf-8"))
    assert "payload_sha256" in event
    assert "payload_preview" not in event
    assert "SECRET-UPSTREAM-PAYLOAD" not in captured.err


def test_parser_logs_raw_preview_only_with_debug_and_explicit_opt_in(capsys) -> None:
    configure_logging(Settings(log_format="json", log_level="debug"))
    parser = LewishamParser(include_raw_upstream=True, raw_upstream_max_chars=10)
    raw_body = "{not-json SECRET-UPSTREAM-PAYLOAD"

    with pytest.raises(UpstreamScraperChangedError):
        parser.parse_collection_schedule(raw_body, reference_date=_REFERENCE_DATE)

    captured = capsys.readouterr()
    event = json_events(captured.err)[0]

    assert event["payload_preview"] == raw_body[:10]
    assert event["payload_truncated"] is True


def test_parser_skips_raw_preview_when_debug_is_disabled(capsys) -> None:
    configure_logging(Settings(log_format="json", log_level="info"))
    parser = LewishamParser(include_raw_upstream=True, raw_upstream_max_chars=10)
    raw_body = "{not-json SECRET-UPSTREAM-PAYLOAD"

    with pytest.raises(UpstreamScraperChangedError):
        parser.parse_collection_schedule(raw_body, reference_date=_REFERENCE_DATE)

    captured = capsys.readouterr()
    event = json_events(captured.err)[0]

    assert "payload_preview" not in event
    assert "SECRET-UPSTREAM-PAYLOAD" not in captured.err


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


def test_parser_normalises_non_breaking_spaces_and_frequency_case() -> None:
    parser = LewishamParser()
    raw_body = encode_html(
        """
        <strong>Food\xa0waste</strong>&nbsp;is collected
        <span class="RoundsTransform">fortnightly</span> on Thursday.
        """
    )

    schedule = parser.parse_collection_schedule(raw_body, reference_date=_REFERENCE_DATE)

    assert schedule.collections[0].waste_type == "Food waste"
    assert schedule.collections[0].frequency == "FORTNIGHTLY"
    assert schedule.collections[0].next_collection is None
