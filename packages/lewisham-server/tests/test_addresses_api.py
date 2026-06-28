import json
from collections.abc import Iterator
from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient

from lewisham_server.api.dependencies import get_lewisham_service
from lewisham_server.domain.errors import (
    InvalidAddressSearchError,
    UpstreamScraperChangedError,
    UpstreamUnavailableError,
)
from lewisham_server.domain.models import AddressCandidate
from lewisham_server.logging_config import configure_logging
from lewisham_server.main import app
from lewisham_server.settings import Settings


class FakeAddressService:
    def __init__(self) -> None:
        self.error: Exception | None = None

    async def lookup_addresses(self, postcode_or_street: str) -> list[AddressCandidate]:
        if self.error is not None:
            raise self.error

        return [
            AddressCandidate(
                uprn="100000000001",
                title=f"1 Example Street, {postcode_or_street}",
            )
        ]


@contextmanager
def api_client(service: FakeAddressService) -> Iterator[TestClient]:
    app.dependency_overrides[get_lewisham_service] = lambda: service
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def test_search_addresses_returns_candidates() -> None:
    service = FakeAddressService()
    with api_client(service) as client:
        response = client.get("/addresses", params={"query": "SE6 1SQ"})

    assert response.status_code == 200
    assert response.json() == [
        {
            "uprn": "100000000001",
            "title": "1 Example Street, SE6 1SQ",
        }
    ]


def test_request_logs_omit_query_values(capsys) -> None:
    configure_logging(Settings(log_format="json", log_level="info"))
    service = FakeAddressService()

    with api_client(service) as client:
        response = client.get("/addresses", params={"query": "SE6 1SQ"})

    assert response.status_code == 200
    captured = capsys.readouterr()
    events = [json.loads(line) for line in captured.out.splitlines()]
    request_event = next(event for event in events if event["event"] == "http_request")

    assert request_event["method"] == "GET"
    assert request_event["route"] == "/addresses"
    assert request_event["status_code"] == 200
    assert "SE6 1SQ" not in captured.out


@pytest.mark.parametrize(
    ("error", "expected_status"),
    [
        (InvalidAddressSearchError("bad search"), 400),
        (UpstreamScraperChangedError("changed"), 502),
        (UpstreamUnavailableError("unavailable"), 503),
    ],
)
def test_search_addresses_maps_domain_errors(
    error: Exception,
    expected_status: int,
) -> None:
    service = FakeAddressService()
    service.error = error

    with api_client(service) as client:
        response = client.get("/addresses", params={"query": "SE6 1SQ"})

    assert response.status_code == expected_status
    assert response.json()["detail"] == str(error)
