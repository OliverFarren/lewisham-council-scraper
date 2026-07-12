import json
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from lewisham_client.domain.errors import (
    AddressNotFoundError,
    CollectionScheduleNotFoundError,
    InvalidUprnError,
    UpstreamScraperChangedError,
    UpstreamUnavailableError,
)
from lewisham_client.domain.models import (
    CollectionEntry,
    CollectionSchedule,
    ContractDriftDiagnostics,
)

from lewisham_server.api.dependencies import get_lewisham_service
from lewisham_server.logging_config import configure_logging
from lewisham_server.main import app
from lewisham_server.settings import Settings


class FakeLewishamService:
    def __init__(self) -> None:
        self.error: Exception | None = None

    async def get_collection_schedule(self, uprn: str) -> CollectionSchedule:
        if self.error is not None:
            raise self.error

        return CollectionSchedule(
            uprn=uprn,
            address="1 Example Street, London",
            collections=[
                CollectionEntry(
                    waste_type="Refuse",
                    frequency="FORTNIGHTLY",
                    day="Thursday",
                    next_collection=None,
                    next_collection_basis=None,
                )
            ],
            source_url="https://lewisham.gov.uk/example",
            fetched_at=datetime(2026, 6, 26, 12, 0, tzinfo=UTC),
        )


@contextmanager
def api_client(service: FakeLewishamService) -> Iterator[TestClient]:
    app.dependency_overrides[get_lewisham_service] = lambda: service
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def test_get_collection_schedule_returns_schedule() -> None:
    service = FakeLewishamService()
    with api_client(service) as client:
        response = client.get("/bins/100000000001/collections")

    assert response.status_code == 200
    assert response.json() == {
        "uprn": "100000000001",
        "address": "1 Example Street, London",
        "collections": [
            {
                "waste_type": "Refuse",
                "frequency": "FORTNIGHTLY",
                "day": "Thursday",
                "next_collection": None,
                "next_collection_basis": None,
            }
        ],
        "source_url": "https://lewisham.gov.uk/example",
        "fetched_at": "2026-06-26T12:00:00Z",
    }


def test_request_logs_use_route_template_without_sensitive_values(capsys) -> None:
    configure_logging(Settings(log_format="json", log_level="info"))
    service = FakeLewishamService()

    with api_client(service) as client:
        response = client.get("/bins/100000000001/collections")

    assert response.status_code == 200
    captured = capsys.readouterr()
    events = [json.loads(line) for line in captured.out.splitlines()]
    request_event = next(event for event in events if event["event"] == "http_request")
    domain_event = next(
        event for event in events if event["event"] == "schedule_lookup_completed"
    )

    assert request_event["method"] == "GET"
    assert request_event["route"] == "/bins/{uprn}/collections"
    assert request_event["status_code"] == 200
    assert domain_event["collection_count"] == 1
    assert domain_event["source_url"] == "https://lewisham.gov.uk/example"
    assert domain_event["fetched_at"] == "2026-06-26T12:00:00+00:00"
    assert domain_event["level"] == "info"
    assert "100000000001" not in captured.out
    assert "1 Example Street" not in captured.out


def test_bins_root_returns_404() -> None:
    service = FakeLewishamService()
    with api_client(service) as client:
        response = client.get("/bins/")

    assert response.status_code == 404


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
    service = FakeLewishamService()
    service.error = error

    with api_client(service) as client:
        response = client.get("/bins/100000000001/collections")

    assert response.status_code == expected_status
    assert response.json()["detail"] == str(error)


def test_fresh_empty_schedule_logs_warning_but_cached_miss_does_not(capsys) -> None:
    configure_logging(Settings(log_format="json", log_level="info"))
    service = FakeLewishamService()
    service.error = CollectionScheduleNotFoundError(
        "missing schedule",
        diagnostics=ContractDriftDiagnostics(
            error_type="CollectionScheduleNotFoundError",
            error_message="missing schedule",
            source="parser",
            payload_size_bytes=42,
            payload_sha256="abc123",
        ),
    )

    with api_client(service) as client:
        response = client.get("/bins/100000000001/collections")

    assert response.status_code == 404
    captured = capsys.readouterr()
    events = [json.loads(line) for line in captured.err.splitlines()]
    event = next(event for event in events if event["event"] == "parser_schedule_empty")
    assert event["level"] == "warning"
    assert event["payload_size_bytes"] == 42
    assert event["payload_sha256"] == "abc123"

    service.error = CollectionScheduleNotFoundError("missing schedule")
    with api_client(service) as client:
        response = client.get("/bins/100000000001/collections")

    assert response.status_code == 404
    captured = capsys.readouterr()
    events = [json.loads(line) for line in captured.err.splitlines()]
    assert all(event["event"] != "parser_schedule_empty" for event in events)
