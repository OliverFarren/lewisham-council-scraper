from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, date, datetime

import pytest
from fastapi.testclient import TestClient

from lewisham_server.api.dependencies import get_bins_service
from lewisham_server.domain.errors import (
    AddressNotFoundError,
    CollectionScheduleNotFoundError,
    InvalidAddressSearchError,
    InvalidUprnError,
    UpstreamScraperChangedError,
    UpstreamUnavailableError,
)
from lewisham_server.domain.models import (
    AddressCandidate,
    CollectionEntry,
    CollectionSchedule,
)
from lewisham_server.main import app


class FakeBinsService:
    def __init__(self) -> None:
        self.address_error: Exception | None = None
        self.schedule_error: Exception | None = None

    async def lookup_addresses(self, postcode_or_street: str) -> list[AddressCandidate]:
        if self.address_error is not None:
            raise self.address_error

        return [
            AddressCandidate(
                uprn="100000000001",
                title=f"1 Example Street, {postcode_or_street}",
            )
        ]

    async def get_collection_schedule(self, uprn: str) -> CollectionSchedule:
        if self.schedule_error is not None:
            raise self.schedule_error

        return CollectionSchedule(
            uprn=uprn,
            address="1 Example Street, London",
            collections=[
                CollectionEntry(
                    waste_type="Refuse",
                    frequency="FORTNIGHTLY",
                    day="Thursday",
                )
            ],
            next_collection=date(2026, 7, 2),
            source_url="https://lewisham.gov.uk/example",
            fetched_at=datetime(2026, 6, 26, 12, 0, tzinfo=UTC),
        )


@contextmanager
def api_client(service: FakeBinsService) -> Iterator[TestClient]:
    app.dependency_overrides[get_bins_service] = lambda: service
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def test_lookup_addresses_returns_candidates() -> None:
    service = FakeBinsService()
    with api_client(service) as client:
        response = client.get("/bins/addresses", params={"postcode": "SE6 1SQ"})

    assert response.status_code == 200
    assert response.json() == [
        {
            "uprn": "100000000001",
            "title": "1 Example Street, SE6 1SQ",
        }
    ]


def test_get_collection_schedule_returns_schedule() -> None:
    service = FakeBinsService()
    with api_client(service) as client:
        response = client.get("/bins/addresses/100000000001/collections")

    assert response.status_code == 200
    assert response.json() == {
        "uprn": "100000000001",
        "address": "1 Example Street, London",
        "collections": [
            {
                "waste_type": "Refuse",
                "frequency": "FORTNIGHTLY",
                "day": "Thursday",
            }
        ],
        "next_collection": "2026-07-02",
        "source_url": "https://lewisham.gov.uk/example",
        "fetched_at": "2026-06-26T12:00:00Z",
    }


def test_bins_root_placeholder_is_removed() -> None:
    service = FakeBinsService()
    with api_client(service) as client:
        response = client.get("/bins/")

    assert response.status_code == 404


@pytest.mark.parametrize(
    ("error", "expected_status"),
    [
        (InvalidAddressSearchError("bad search"), 400),
        (UpstreamScraperChangedError("changed"), 502),
        (UpstreamUnavailableError("unavailable"), 503),
    ],
)
def test_lookup_addresses_maps_domain_errors(
    error: Exception,
    expected_status: int,
) -> None:
    service = FakeBinsService()
    service.address_error = error

    with api_client(service) as client:
        response = client.get("/bins/addresses", params={"postcode": "SE6 1SQ"})

    assert response.status_code == expected_status
    assert response.json()["detail"] == str(error)


@pytest.mark.parametrize(
    ("error", "expected_status"),
    [
        (InvalidUprnError("bad uprn"), 400),
        (AddressNotFoundError("missing address"), 404),
        (CollectionScheduleNotFoundError("missing schedule"), 404),
        (UpstreamScraperChangedError("changed"), 502),
        (UpstreamUnavailableError("unavailable"), 503),
    ],
)
def test_get_collection_schedule_maps_domain_errors(
    error: Exception,
    expected_status: int,
) -> None:
    service = FakeBinsService()
    service.schedule_error = error

    with api_client(service) as client:
        response = client.get("/bins/addresses/100000000001/collections")

    assert response.status_code == expected_status
    assert response.json()["detail"] == str(error)
