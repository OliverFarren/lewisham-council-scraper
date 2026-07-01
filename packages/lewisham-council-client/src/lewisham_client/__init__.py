"""Lewisham Council civic-data client.

Provides asynchronous access to Lewisham's waste collection schedules and
address resolution. Adapters (FastAPI, Home Assistant, MCP) depend on this
package; this package has no dependency on any of them.

Typical use::

    from lewisham_client import LewishamService

    service = LewishamService()
    addresses = await service.lookup_addresses("SE6 1SQ")
    schedule = await service.get_collection_schedule(addresses[0].uprn)
    await service.aclose()
"""

from lewisham_client.clients.lewisham.client import LewishamClient
from lewisham_client.clients.lewisham.config import (
    BASE_URL,
    COLLECTION_PAGE_URL,
    REQUEST_TIMEOUT_SECONDS,
    ROUNDS_INFORMATION_ITEM_GUID,
    USER_AGENT,
)
from lewisham_client.clients.lewisham.models import (
    CollectionScheduleRaw,
    ParsedCollectionSchedule,
)
from lewisham_client.clients.lewisham.parser import LewishamParser
from lewisham_client.domain.errors import (
    AddressNotFoundError,
    CollectionScheduleNotFoundError,
    DomainError,
    InvalidAddressSearchError,
    InvalidUprnError,
    UpstreamScraperChangedError,
    UpstreamUnavailableError,
    find_diagnostics,
)
from lewisham_client.domain.models import (
    AddressCandidate,
    CollectionEntry,
    CollectionSchedule,
    ContractDriftDiagnostics,
    DataQualitySummary,
)
from lewisham_client.services.lewisham_service import LewishamService, LewishamSource
from lewisham_client.storage.cache_interface import TtlCache
from lewisham_client.storage.memory_cache import MemoryTtlCache

__all__ = [
    # Service
    "LewishamService",
    "LewishamSource",
    # HTTP client and parser
    "LewishamClient",
    "LewishamParser",
    "CollectionScheduleRaw",
    "ParsedCollectionSchedule",
    # Domain models
    "AddressCandidate",
    "CollectionEntry",
    "CollectionSchedule",
    "ContractDriftDiagnostics",
    "DataQualitySummary",
    # Domain errors
    "DomainError",
    "AddressNotFoundError",
    "CollectionScheduleNotFoundError",
    "InvalidAddressSearchError",
    "InvalidUprnError",
    "UpstreamScraperChangedError",
    "UpstreamUnavailableError",
    "find_diagnostics",
    # Storage
    "TtlCache",
    "MemoryTtlCache",
    # Upstream config defaults (consumed by lewisham-server settings)
    "BASE_URL",
    "COLLECTION_PAGE_URL",
    "REQUEST_TIMEOUT_SECONDS",
    "ROUNDS_INFORMATION_ITEM_GUID",
    "USER_AGENT",
]
