import json
from datetime import date

import pytest

from lewisham_server.clients.lewisham import LewishamParser
from lewisham_server.domain.errors import (
    CollectionScheduleNotFoundError,
    UpstreamScraperChangedError,
)


def encode_html(fragment: str) -> str:
    return json.dumps(fragment)


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

    schedule = parser.parse_collection_schedule(raw_body)

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
    assert schedule.next_collection == date(2026, 7, 2)


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
        parser.parse_collection_schedule(raw_body)


def test_parser_allows_partial_civic_schedule_without_next_date() -> None:
    parser = LewishamParser()
    raw_body = encode_html(
        """
        <strong>Recycling</strong>&nbsp;is collected
        <span class="RoundsTransform">WEEKLY</span> on Monday.
        """
    )

    schedule = parser.parse_collection_schedule(raw_body)

    assert len(schedule.collections) == 1
    assert schedule.collections[0].waste_type == "Recycling"
    assert schedule.next_collection is None


def test_parser_rejects_malformed_json() -> None:
    parser = LewishamParser()

    with pytest.raises(UpstreamScraperChangedError):
        parser.parse_collection_schedule("{not-json")


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
        parser.parse_collection_schedule(raw_body)


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
        parser.parse_collection_schedule(raw_body)


def test_parser_normalises_non_breaking_spaces_and_frequency_case() -> None:
    parser = LewishamParser()
    raw_body = encode_html(
        """
        <strong>Food\xa0waste</strong>&nbsp;is collected
        <span class="RoundsTransform">fortnightly</span> on Thursday.
        """
    )

    schedule = parser.parse_collection_schedule(raw_body)

    assert schedule.collections[0].waste_type == "Food waste"
    assert schedule.collections[0].frequency == "FORTNIGHTLY"
