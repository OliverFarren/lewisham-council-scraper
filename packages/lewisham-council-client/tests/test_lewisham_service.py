import json
import logging
from datetime import UTC, datetime, timedelta

import pytest

from lewisham_client.clients.lewisham import CollectionScheduleRaw
from lewisham_client.domain.errors import CollectionScheduleNotFoundError
from lewisham_client.domain.models import AddressCandidate
from lewisham_client.services import LewishamService
from lewisham_client.storage import MemoryTtlCache

_SERVICE_LOGGER = "lewisham_client.services.lewisham_service"


class MutableClock:
    def __init__(self) -> None:
        self.current = datetime(2026, 6, 26, 12, 0, tzinfo=UTC)

    def __call__(self) -> datetime:
        return self.current

    def advance(self, delta: timedelta) -> None:
        self.current += delta


class FakeLewishamClient:
    def __init__(
        self,
        *,
        addresses: list[AddressCandidate] | None = None,
        address: AddressCandidate | None = None,
        raw_body: str | None = None,
    ) -> None:
        self.addresses = addresses or []
        self.address = address
        self.raw_body = raw_body or residential_body()
        self.lookup_calls = 0
        self.address_calls = 0
        self.schedule_calls = 0
        self.closed = False

    async def lookup_addresses(
        self,
        postcode_or_street: str,
    ) -> list[AddressCandidate]:
        self.lookup_calls += 1
        return list(self.addresses)

    async def get_address(self, uprn: str) -> AddressCandidate:
        self.address_calls += 1
        if self.address is None:
            return AddressCandidate(uprn=uprn, title="1 Example Street")
        return self.address

    async def get_collection_schedule(self, uprn: str) -> CollectionScheduleRaw:
        self.schedule_calls += 1
        return CollectionScheduleRaw(
            uprn=uprn,
            body=self.raw_body,
            source_url="https://lewisham.gov.uk/example",
            fetched_at=datetime(2026, 6, 26, 12, 0, tzinfo=UTC),
        )

    async def aclose(self) -> None:
        self.closed = True


def residential_body() -> str:
    return json.dumps(
        """
        <strong>Refuse</strong>&nbsp;is collected
        <span class="RoundsTransform">FORTNIGHTLY</span> on Thursday.
        Your next collection date is 02/07/2026.
        """
    )


def empty_schedule_body() -> str:
    return json.dumps("<p>If the above is incorrect please notify us</p>")


def _event_records(
    caplog: pytest.LogCaptureFixture,
    event: str,
) -> list[logging.LogRecord]:
    return [
        record
        for record in caplog.records
        if record.name == _SERVICE_LOGGER and record.getMessage() == event
    ]


@pytest.mark.asyncio
async def test_service_caches_successful_schedule() -> None:
    clock = MutableClock()
    client = FakeLewishamClient()
    service = LewishamService(client=client, clock=clock)

    first = await service.get_collection_schedule("100000000001")
    second = await service.get_collection_schedule("100000000001")

    assert first is second
    assert client.address_calls == 1
    assert client.schedule_calls == 1


@pytest.mark.asyncio
async def test_lookup_addresses_caches_results_and_populates_address_cache() -> None:
    clock = MutableClock()
    address = AddressCandidate(uprn="100000000001", title="1 Example Street")
    client = FakeLewishamClient(addresses=[address])
    service = LewishamService(client=client, clock=clock)

    addresses = await service.lookup_addresses("SE6 1SQ")
    schedule = await service.get_collection_schedule("100000000001")

    assert addresses == [address]
    assert schedule.address == "1 Example Street"
    assert client.lookup_calls == 1
    assert client.address_calls == 0
    assert client.schedule_calls == 1


@pytest.mark.asyncio
async def test_client_writes_nothing_without_logging_configuration(
    capsys: pytest.CaptureFixture[str],
) -> None:
    service = LewishamService(
        client=FakeLewishamClient(
            addresses=[
                AddressCandidate(
                    uprn="100000000001",
                    title="1 Example Street",
                )
            ]
        )
    )

    await service.lookup_addresses("SE6 1SQ")

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""


@pytest.mark.asyncio
async def test_lookup_addresses_logs_safe_cache_and_completion_events(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.DEBUG, logger=_SERVICE_LOGGER)
    clock = MutableClock()
    address = AddressCandidate(uprn="100000000001", title="1 Example Street")
    client = FakeLewishamClient(addresses=[address])
    service = LewishamService(client=client, clock=clock)

    await service.lookup_addresses("SE6 1SQ")
    await service.lookup_addresses("SE6 1SQ")

    event_names = [
        record.getMessage()
        for record in caplog.records
        if record.name == _SERVICE_LOGGER
    ]

    assert "cache_miss" in event_names
    assert "cache_store" in event_names
    assert "cache_hit" in event_names
    assert event_names.count("address_lookup_completed") == 2
    assert all(record.levelno == logging.DEBUG for record in caplog.records)
    captured_records = repr([record.__dict__ for record in caplog.records])
    assert "SE6 1SQ" not in captured_records
    assert "100000000001" not in captured_records
    assert "1 Example Street" not in captured_records


@pytest.mark.asyncio
async def test_get_collection_schedule_logs_safe_completion_event(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.DEBUG, logger=_SERVICE_LOGGER)
    clock = MutableClock()
    client = FakeLewishamClient()
    service = LewishamService(client=client, clock=clock)

    await service.get_collection_schedule("100000000001")

    completion_event = _event_records(caplog, "schedule_lookup_completed")[0]

    assert completion_event.levelno == logging.DEBUG
    assert completion_event.collection_count == 1
    captured_records = repr([record.__dict__ for record in caplog.records])
    assert "100000000001" not in captured_records
    assert "1 Example Street" not in captured_records


@pytest.mark.asyncio
async def test_lookup_addresses_caches_negative_results() -> None:
    clock = MutableClock()
    client = FakeLewishamClient(addresses=[])
    service = LewishamService(client=client, clock=clock)

    first = await service.lookup_addresses("INVALID")
    second = await service.lookup_addresses("INVALID")

    assert first == []
    assert second == []
    assert client.lookup_calls == 1


@pytest.mark.asyncio
async def test_service_caches_negative_schedule_results() -> None:
    clock = MutableClock()
    client = FakeLewishamClient(raw_body=empty_schedule_body())
    service = LewishamService(client=client, clock=clock)

    with pytest.raises(CollectionScheduleNotFoundError):
        await service.get_collection_schedule("100000000001")

    with pytest.raises(CollectionScheduleNotFoundError):
        await service.get_collection_schedule("100000000001")

    assert client.address_calls == 1
    assert client.schedule_calls == 1


@pytest.mark.asyncio
async def test_schedule_not_found_diagnostics_only_from_parser_failure() -> None:
    """The parser-sourced failure carries diagnostics; the cached one does not."""
    clock = MutableClock()
    client = FakeLewishamClient(raw_body=empty_schedule_body())
    service = LewishamService(client=client, clock=clock)

    with pytest.raises(CollectionScheduleNotFoundError) as first_exc_info:
        await service.get_collection_schedule("100000000001")

    with pytest.raises(CollectionScheduleNotFoundError) as second_exc_info:
        await service.get_collection_schedule("100000000001")

    assert first_exc_info.value.diagnostics is not None
    assert first_exc_info.value.diagnostics.payload_sha256 is not None
    assert second_exc_info.value.diagnostics is None


@pytest.mark.asyncio
async def test_schedule_cache_expires_after_ttl() -> None:
    clock = MutableClock()
    client = FakeLewishamClient()
    service = LewishamService(client=client, clock=clock)

    await service.get_collection_schedule("100000000001")
    clock.advance(timedelta(hours=25))
    await service.get_collection_schedule("100000000001")

    assert client.schedule_calls == 2


def test_memory_cache_expires_values() -> None:
    clock = MutableClock()
    cache = MemoryTtlCache[str, str](clock=clock)

    cache.set("key", "value", timedelta(seconds=1))
    assert cache.get("key") == "value"

    clock.advance(timedelta(seconds=2))
    assert cache.get("key") is None
