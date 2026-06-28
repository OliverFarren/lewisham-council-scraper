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
If the host application already manages a session (for example, Home Assistant's
`aiohttp` session or a shared httpx client), pass it via `LewishamClient`:

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

## Caching

`LewishamService` uses an in-process `MemoryTtlCache` by default with
conservative TTLs (schedules: 24 h, address searches: 7 d, UPRNs: 30 d,
negative results: 1 h). The defaults are suitable for a single-process consumer
such as a Home Assistant integration.

Injectable cache and TTL parameters are available for consumers that need
different policy or a shared cache.
