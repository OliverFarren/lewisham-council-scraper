# lewisham-council-client

Framework-neutral Python client for Lewisham Council civic data. Provides
asynchronous address resolution and waste collection schedule retrieval for any
Lewisham UPRN.

No dependency on FastAPI, Home Assistant, MCP, uvicorn, or any web framework.
Designed to be embedded directly in another Python application.

> **Unofficial** — not affiliated with or endorsed by Lewisham Council. Uses
> undocumented public endpoints that may change without notice; the client
> raises `UpstreamScraperChangedError` when the response shape no longer
> matches expectations.

## Installation

```bash
pip install lewisham-council-client
```

## Usage

```python
import asyncio
from lewisham_client import LewishamService

async def main() -> None:
    service = LewishamService()
    try:
        addresses = await service.lookup_addresses("SE6 1SQ")
        for address in addresses:
            print(address.uprn, address.title)

        if addresses:
            schedule = await service.get_collection_schedule(addresses[0].uprn)
            for entry in schedule.collections:
                print(entry.waste_type, entry.frequency, entry.next_collection)
    finally:
        await service.aclose()

asyncio.run(main())
```

`LewishamService` creates and manages its own `httpx.AsyncClient` by default.
If the host application already manages a shared `httpx.AsyncClient`, pass it
via `LewishamClient`:

```python
import httpx
from lewisham_client import LewishamClient, LewishamService

async with httpx.AsyncClient() as http:
    service = LewishamService(client=LewishamClient(http_client=http))
    schedule = await service.get_collection_schedule(uprn)
```

## Errors

All errors are subclasses of `lewisham_client.DomainError`:

| Exception | When |
| --- | --- |
| `InvalidAddressSearchError` | Search input is too short or malformed. |
| `InvalidUprnError` | UPRN is not a non-empty decimal string. |
| `AddressNotFoundError` | No Lewisham address found for the given UPRN. |
| `CollectionScheduleNotFoundError` | Lewisham returned no parseable schedule for the address. |
| `UpstreamScraperChangedError` | Lewisham's response shape no longer matches expectations. |
| `UpstreamUnavailableError` | Lewisham could not be reached (timeout or transport error). |

## Diagnostics

Every `DomainError` carries a `diagnostics: ContractDriftDiagnostics | None`
attribute — useful for building a rich failure report without intercepting
log output. It is set automatically by `LewishamParser`/`LewishamClient` when
the failure was an upstream contract-drift (a parse failure or an unexpected
HTTP response) and `None` otherwise — e.g. for validation errors,
address-not-found errors, and cached negative results that did not
themselves re-parse a payload:

```python
from lewisham_client import LewishamParser, LewishamService, UpstreamScraperChangedError

service = LewishamService(parser=LewishamParser(include_raw_upstream=True))
try:
    schedule = await service.get_collection_schedule(uprn)
except UpstreamScraperChangedError as err:
    if err.diagnostics is not None:
        print(err.diagnostics.source)            # "client" or "parser"
        print(err.diagnostics.payload_sha256)     # always populated, no PII
        print(err.diagnostics.payload_preview)    # parser only, opted in above
```

`source` (`"client"` or `"parser"`) tells you which other fields to expect:
`"client"` diagnostics (an unexpected HTTP status, or a response
`LewishamClient` itself could not decode/shape-validate) always populate
`status_code`/`endpoint`; `"parser"` diagnostics (`LewishamParser` could not
extract entries from the decoded HTML) never do. `payload_size_bytes` and
`payload_sha256` are always populated and never contain PII.
`payload_preview` (a truncated slice of the raw upstream body, which *may*
contain PII scraped from the page) is only populated for `"parser"`
diagnostics when the parser was constructed with `include_raw_upstream=True`
— this is independent of the `logging` module's level, unlike the
`parser_contract_drift` log event, which additionally requires the
`lewisham_client.clients.lewisham.parser` logger to be at `DEBUG`.

If a consumer wraps our exceptions in its own type — whether via explicit
`raise SomeError(...) from err` or a bare `raise SomeError(...)` inside an
`except` block — use `find_diagnostics` instead of catching the library's
exceptions directly. It walks both the `__cause__` and `__context__` chains
for you, preferring the more specific `__cause__` when both are set:

```python
from lewisham_client import find_diagnostics

diagnostics = find_diagnostics(caught_exception)
```

`CollectionSchedule.data_quality()` returns a `DataQualitySummary` — counts
of entries whose `next_collection` came from a council-published date vs. a
derived weekday guess vs. nothing published — for a consumer that wants to
report on schedule confidence without re-deriving it from
`next_collection_basis` itself:

```python
summary = schedule.data_quality()
print(summary.published_count, summary.weekday_derived_count)
```

## Logging

The client uses Python's standard `logging` package and does not configure
handlers, formatting, destinations, or process-wide levels. Cache activity,
upstream request metadata, parser diagnostics, and operation outcomes are
available at `DEBUG`:

```python
import logging

logging.basicConfig(level=logging.DEBUG)
logging.getLogger("lewisham_client").setLevel(logging.DEBUG)
```

Structured context is attached to each `LogRecord` through `extra`, so a host
application can render it as text or JSON. Raised `DomainError` exceptions do
not also produce warning or error records from the client; the host decides
how visibly to report the operation it is handling.

## Caching

`LewishamService` uses an in-process `MemoryTtlCache` by default with
conservative TTLs (schedules: 24 h, address searches: 7 d, UPRNs: 30 d,
negative results: 1 h). The defaults are suitable for a single-process consumer
such as a Home Assistant integration.

Injectable cache and TTL parameters are available for consumers that need
different policy or a shared cache.
