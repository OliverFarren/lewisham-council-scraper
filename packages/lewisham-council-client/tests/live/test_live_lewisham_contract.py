import os

import pytest

from lewisham_client import LewishamClient, LewishamService
from lewisham_client.domain.errors import DomainError, find_diagnostics

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(
        os.environ.get("LEWISHAM_RUN_LIVE_TESTS") != "1",
        reason="live Lewisham endpoint checks are opt-in",
    ),
]

_PUBLIC_CIVIC_POSTCODE = "SE6 4RU"


@pytest.mark.asyncio
async def test_live_addressfinder_contract_for_public_civic_postcode() -> None:
    client = LewishamClient()
    try:
        addresses = await client.lookup_addresses(_PUBLIC_CIVIC_POSTCODE)
    finally:
        await client.aclose()

    assert addresses
    assert all(address.uprn.isdecimal() and address.title for address in addresses)


@pytest.mark.asyncio
async def test_live_collection_schedule_contract_for_secret_uprn() -> None:
    uprn = os.environ.get("LEWISHAM_LIVE_TEST_UPRN", "").strip()
    if not uprn:
        pytest.skip("LEWISHAM_LIVE_TEST_UPRN is not configured")

    service = LewishamService()
    try:
        schedule = await service.get_collection_schedule(uprn)
    except DomainError as exc:
        pytest.fail(_redacted_domain_failure(exc), pytrace=False)
    finally:
        await service.aclose()

    assert schedule.collections
    assert schedule.source_url.startswith("https://lewisham.gov.uk/")
    assert all(collection.waste_type for collection in schedule.collections)
    assert all(
        collection.frequency in {"WEEKLY", "FORTNIGHTLY"}
        for collection in schedule.collections
    )
    assert all(collection.day for collection in schedule.collections)


def _redacted_domain_failure(exc: DomainError) -> str:
    diagnostics = find_diagnostics(exc)
    if diagnostics is None:
        return (
            "Lewisham live schedule check failed with "
            f"{type(exc).__name__}; UPRN redacted."
        )

    details = [
        f"endpoint={diagnostics.endpoint}",
        f"status_code={diagnostics.status_code}",
        f"payload_size_bytes={diagnostics.payload_size_bytes}",
        f"payload_sha256={diagnostics.payload_sha256}",
        f"duration_ms={diagnostics.duration_ms}",
    ]
    return (
        "Lewisham live schedule check failed with "
        f"{type(exc).__name__}; UPRN redacted; "
        + ", ".join(detail for detail in details if not detail.endswith("=None"))
    )
