"""Tests for domain model computed behavior."""

from __future__ import annotations

from datetime import date, datetime

from lewisham_client.domain.models import (
    CollectionEntry,
    CollectionSchedule,
    DataQualitySummary,
)


def _schedule(collections: list[CollectionEntry]) -> CollectionSchedule:
    return CollectionSchedule(
        uprn="100000000001",
        address="1 Example Street",
        collections=collections,
        source_url="https://lewisham.gov.uk/example",
        fetched_at=datetime(2026, 6, 26, 12, 0),
    )


def test_data_quality_counts_published_weekday_derived_and_missing() -> None:
    schedule = _schedule(
        [
            CollectionEntry(
                waste_type="Food Waste",
                frequency="WEEKLY",
                day="Monday",
                next_collection=date(2026, 7, 7),
                next_collection_basis="published",
            ),
            CollectionEntry(
                waste_type="Recycling",
                frequency="WEEKLY",
                day="Monday",
                next_collection=date(2026, 6, 29),
                next_collection_basis="weekday_derived",
            ),
            CollectionEntry(
                waste_type="Refuse",
                frequency="FORTNIGHTLY",
                day="Monday",
                next_collection=None,
                next_collection_basis=None,
            ),
        ]
    )

    assert schedule.data_quality() == DataQualitySummary(
        total_collections=3,
        published_count=1,
        weekday_derived_count=1,
        missing_next_collection_count=1,
    )


def test_data_quality_of_empty_schedule_is_all_zero() -> None:
    schedule = _schedule([])
    assert schedule.data_quality() == DataQualitySummary(0, 0, 0, 0)
