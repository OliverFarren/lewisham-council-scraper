import json
import logging
from datetime import UTC, datetime

import httpx
import pytest

from lewisham_client.clients.lewisham import LewishamClient
from lewisham_client.clients.lewisham.config import (
    ADDRESS_FINDER_PATH,
    ROUNDS_INFORMATION_PATH,
    USER_AGENT,
)
from lewisham_client.domain.errors import (
    InvalidAddressSearchError,
    InvalidUprnError,
    UpstreamScraperChangedError,
    UpstreamUnavailableError,
)

_CLIENT_LOGGER = "lewisham_client.clients.lewisham.client"


def fixed_clock() -> datetime:
    return datetime(2026, 6, 26, 12, 0, tzinfo=UTC)


def _event_record(
    caplog: pytest.LogCaptureFixture,
    event: str,
) -> logging.LogRecord:
    return next(
        record
        for record in caplog.records
        if record.name == _CLIENT_LOGGER and record.getMessage() == event
    )


@pytest.mark.asyncio
async def test_lookup_addresses_returns_normalised_candidates() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json=[
                {
                    "Uprn": 100000000001,
                    "Title": "  1,\xa0Example Street,  SE6 1SQ  ",
                }
            ],
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        client = LewishamClient(http_client=http, clock=fixed_clock)
        addresses = await client.lookup_addresses(" SE6\xa01SQ ")

    assert addresses[0].uprn == "100000000001"
    assert addresses[0].title == "1, Example Street, SE6 1SQ"
    assert requests[0].url.path == ADDRESS_FINDER_PATH
    assert requests[0].url.params["postcodeOrStreet"] == "SE6 1SQ"
    assert requests[0].url.params["national"] == "False"
    assert requests[0].headers["user-agent"] == USER_AGENT


@pytest.mark.asyncio
async def test_client_logs_upstream_request_and_response_metadata(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.DEBUG, logger=_CLIENT_LOGGER)

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["postcodeOrStreet"] == "SE6 1SQ"
        return httpx.Response(
            200,
            json=[{"Uprn": 100000000001, "Title": "1 Example Street"}],
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        client = LewishamClient(http_client=http, clock=fixed_clock)
        await client.lookup_addresses("SE6 1SQ")

    request_event = _event_record(caplog, "upstream_request")
    response_event = _event_record(caplog, "upstream_response")

    assert request_event.levelno == logging.DEBUG
    assert request_event.endpoint == "AddressFinder"
    assert request_event.upstream_path == ADDRESS_FINDER_PATH
    assert response_event.levelno == logging.DEBUG
    assert response_event.status_code == 200
    assert response_event.response_size_bytes > 0
    captured_records = repr([record.__dict__ for record in caplog.records])
    assert "SE6 1SQ" not in captured_records
    assert "100000000001" not in captured_records
    assert "1 Example Street" not in captured_records


@pytest.mark.asyncio
async def test_get_address_returns_candidate() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == ADDRESS_FINDER_PATH
        assert request.url.params["uprn"] == "100000000001"
        return httpx.Response(
            200,
            json={"Uprn": "100000000001", "Title": "1 Example Street"},
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        client = LewishamClient(http_client=http, clock=fixed_clock)
        address = await client.get_address("100000000001")

    assert address.uprn == "100000000001"
    assert address.title == "1 Example Street"


@pytest.mark.asyncio
async def test_get_collection_schedule_returns_raw_response() -> None:
    raw_body = json.dumps("<h2>When your bins are collected:</h2>")

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == ROUNDS_INFORMATION_PATH
        assert request.url.params["uprn"] == "100000000001"
        assert "item" in request.url.params
        return httpx.Response(200, text=raw_body)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        client = LewishamClient(http_client=http, clock=fixed_clock)
        schedule = await client.get_collection_schedule("100000000001")

    assert schedule.uprn == "100000000001"
    assert schedule.body == raw_body
    assert schedule.fetched_at == fixed_clock()


@pytest.mark.asyncio
async def test_lookup_addresses_rejects_short_input_without_http_call() -> None:
    called = False

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal called
        called = True
        return httpx.Response(200, json=[])

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        client = LewishamClient(http_client=http, clock=fixed_clock)
        with pytest.raises(InvalidAddressSearchError):
            await client.lookup_addresses("SE")

    assert called is False


@pytest.mark.asyncio
async def test_get_collection_schedule_rejects_invalid_uprn_without_http_call() -> None:
    called = False

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal called
        called = True
        return httpx.Response(200, text=json.dumps(""))

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        client = LewishamClient(http_client=http, clock=fixed_clock)
        with pytest.raises(InvalidUprnError):
            await client.get_collection_schedule("not-a-uprn")

    assert called is False


@pytest.mark.asyncio
async def test_lookup_addresses_rejects_malformed_payload() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[{"Uprn": 100000000001}])

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        client = LewishamClient(http_client=http, clock=fixed_clock)
        with pytest.raises(UpstreamScraperChangedError) as exc_info:
            await client.lookup_addresses("SE6 1SQ")

    diagnostics = exc_info.value.diagnostics
    assert diagnostics is not None
    assert diagnostics.source == "client"
    assert diagnostics.endpoint == "AddressFinder"
    assert diagnostics.payload_sha256 is not None


@pytest.mark.asyncio
async def test_lookup_addresses_rejects_non_list_payload_with_diagnostics() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"not": "a list"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        client = LewishamClient(http_client=http, clock=fixed_clock)
        with pytest.raises(UpstreamScraperChangedError) as exc_info:
            await client.lookup_addresses("SE6 1SQ")

    diagnostics = exc_info.value.diagnostics
    assert diagnostics is not None
    assert diagnostics.source == "client"
    assert diagnostics.endpoint == "AddressFinder"


@pytest.mark.asyncio
async def test_lookup_addresses_rejects_invalid_json_with_diagnostics() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="not-json")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        client = LewishamClient(http_client=http, clock=fixed_clock)
        with pytest.raises(UpstreamScraperChangedError) as exc_info:
            await client.lookup_addresses("SE6 1SQ")

    diagnostics = exc_info.value.diagnostics
    assert diagnostics is not None
    assert diagnostics.source == "client"
    assert diagnostics.payload_sha256 is not None


@pytest.mark.asyncio
async def test_client_logs_upstream_contract_drift_without_payload(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.DEBUG, logger=_CLIENT_LOGGER)

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[{"Uprn": 100000000001}])

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        client = LewishamClient(http_client=http, clock=fixed_clock)
        with pytest.raises(UpstreamScraperChangedError):
            await client.lookup_addresses("SE6 1SQ")

    drift_event = _event_record(caplog, "upstream_contract_drift_detected")

    assert drift_event.levelno == logging.DEBUG
    assert drift_event.endpoint == "AddressFinder"
    assert all(record.levelno < logging.WARNING for record in caplog.records)
    captured_records = repr([record.__dict__ for record in caplog.records])
    assert "SE6 1SQ" not in captured_records
    assert "100000000001" not in captured_records


@pytest.mark.asyncio
async def test_lookup_addresses_treats_http_500_as_scraper_change() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="<html>error</html>")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        client = LewishamClient(http_client=http, clock=fixed_clock)
        with pytest.raises(UpstreamScraperChangedError, match="HTTP 500"):
            await client.lookup_addresses("SE6 1SQ")


@pytest.mark.asyncio
async def test_get_collection_schedule_rejects_unexpected_status() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(404, text="<html>missing</html>")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        client = LewishamClient(http_client=http, clock=fixed_clock)
        with pytest.raises(UpstreamScraperChangedError, match="HTTP 404"):
            await client.get_collection_schedule("100000000001")


@pytest.mark.asyncio
async def test_get_collection_schedule_attaches_status_diagnostics() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(404, text="<html>missing</html>")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        client = LewishamClient(http_client=http, clock=fixed_clock)
        with pytest.raises(UpstreamScraperChangedError) as exc_info:
            await client.get_collection_schedule("100000000001")

    diagnostics = exc_info.value.diagnostics
    assert diagnostics is not None
    assert diagnostics.source == "client"
    assert diagnostics.status_code == 404
    assert diagnostics.endpoint == "roundsinformation"


@pytest.mark.asyncio
async def test_transport_error_becomes_upstream_unavailable_without_visible_log(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.DEBUG, logger=_CLIENT_LOGGER)

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection failed", request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        client = LewishamClient(http_client=http, clock=fixed_clock)
        with pytest.raises(UpstreamUnavailableError) as exc_info:
            await client.lookup_addresses("SE6 1SQ")

    event = _event_record(caplog, "upstream_transport_error")
    assert event.levelno == logging.DEBUG

    diagnostics = exc_info.value.diagnostics
    assert diagnostics is not None
    assert diagnostics.endpoint == "AddressFinder"
    assert diagnostics.error_type == "ConnectError"
    assert diagnostics.duration_ms is not None
    assert all(record.levelno < logging.WARNING for record in caplog.records)
