from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Protocol

from lewisham_server.clients.lewisham import (
    CollectionScheduleRaw,
    LewishamClient,
    LewishamParser,
)
from lewisham_server.domain.errors import (
    AddressNotFoundError,
    CollectionScheduleNotFoundError,
)
from lewisham_server.domain.models import (
    AddressCandidate,
    CollectionSchedule,
)
from lewisham_server.storage import MemoryTtlCache, TtlCache

SCHEDULE_CACHE_TTL = timedelta(hours=24)
ADDRESS_CACHE_TTL = timedelta(days=7)
NEGATIVE_CACHE_TTL = timedelta(hours=1)


def _default_clock() -> datetime:
    return datetime.now(UTC)


class LewishamSource(Protocol):
    async def lookup_addresses(
        self,
        postcode_or_street: str,
    ) -> list[AddressCandidate]: ...

    async def get_address(self, uprn: str) -> AddressCandidate: ...

    async def get_collection_schedule(self, uprn: str) -> CollectionScheduleRaw: ...

    async def aclose(self) -> None: ...


class BinsService:
    """Coordinate Lewisham address lookup, schedule parsing, and cache policy."""

    def __init__(
        self,
        *,
        client: LewishamSource | None = None,
        parser: LewishamParser | None = None,
        address_search_cache: TtlCache[str, list[AddressCandidate]] | None = None,
        address_cache: TtlCache[str, AddressCandidate] | None = None,
        schedule_cache: TtlCache[str, CollectionSchedule] | None = None,
        negative_cache: TtlCache[str, bool] | None = None,
        schedule_cache_ttl: timedelta = SCHEDULE_CACHE_TTL,
        address_cache_ttl: timedelta = ADDRESS_CACHE_TTL,
        negative_cache_ttl: timedelta = NEGATIVE_CACHE_TTL,
        clock: Callable[[], datetime] = _default_clock,
    ) -> None:
        self._client = client or LewishamClient(clock=clock)
        self._parser = parser or LewishamParser()
        self._address_search_cache = address_search_cache or MemoryTtlCache(clock)
        self._address_cache = address_cache or MemoryTtlCache(clock)
        self._schedule_cache = schedule_cache or MemoryTtlCache(clock)
        self._negative_cache = negative_cache or MemoryTtlCache(clock)
        self._schedule_cache_ttl = schedule_cache_ttl
        self._address_cache_ttl = address_cache_ttl
        self._negative_cache_ttl = negative_cache_ttl

    async def lookup_addresses(self, postcode_or_street: str) -> list[AddressCandidate]:
        """Resolve user-entered address text into Lewisham address candidates."""

        search_key = self._key("address-search", postcode_or_street)
        if self._negative_cache.get(search_key) is True:
            return []

        cached_addresses = self._address_search_cache.get(search_key)
        if cached_addresses is not None:
            return list(cached_addresses)

        addresses = await self._client.lookup_addresses(postcode_or_street)
        if not addresses:
            self._negative_cache.set(search_key, True, self._negative_cache_ttl)
            return []

        self._address_search_cache.set(
            search_key,
            list(addresses),
            self._address_cache_ttl,
        )
        for address in addresses:
            self._address_cache.set(
                self._key("address", address.uprn),
                address,
                self._address_cache_ttl,
            )

        return addresses

    async def get_collection_schedule(self, uprn: str) -> CollectionSchedule:
        """Fetch and parse a collection schedule for a Lewisham UPRN."""

        schedule_key = self._key("schedule", uprn)
        if self._negative_cache.get(schedule_key) is True:
            raise CollectionScheduleNotFoundError(
                f"No collection schedule found for UPRN {uprn.strip()}."
            )

        cached_schedule = self._schedule_cache.get(schedule_key)
        if cached_schedule is not None:
            return cached_schedule

        address = await self._get_address(uprn)
        raw_schedule = await self._client.get_collection_schedule(address.uprn)

        try:
            parsed_schedule = self._parser.parse_collection_schedule(raw_schedule.body)
        except CollectionScheduleNotFoundError:
            self._negative_cache.set(schedule_key, True, self._negative_cache_ttl)
            raise

        schedule = CollectionSchedule(
            uprn=address.uprn,
            address=address.title,
            collections=list(parsed_schedule.collections),
            next_collection=parsed_schedule.next_collection,
            source_url=raw_schedule.source_url,
            fetched_at=raw_schedule.fetched_at,
        )
        self._schedule_cache.set(schedule_key, schedule, self._schedule_cache_ttl)
        return schedule

    async def aclose(self) -> None:
        """Close owned network resources when the application shuts down."""

        await self._client.aclose()

    async def _get_address(self, uprn: str) -> AddressCandidate:
        address_key = self._key("address", uprn)
        if self._negative_cache.get(address_key) is True:
            raise AddressNotFoundError(
                f"No Lewisham address found for UPRN {uprn.strip()}."
            )

        cached_address = self._address_cache.get(address_key)
        if cached_address is not None:
            return cached_address

        try:
            address = await self._client.get_address(uprn)
        except AddressNotFoundError:
            self._negative_cache.set(address_key, True, self._negative_cache_ttl)
            raise

        self._address_cache.set(address_key, address, self._address_cache_ttl)
        return address

    @staticmethod
    def _key(namespace: str, value: str) -> str:
        return f"{namespace}:{' '.join(value.casefold().split())}"
