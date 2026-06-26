from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Query, status

from lewisham_server.api.dependencies import BinsServiceDependency
from lewisham_server.api.schemas.bins import (
    AddressCandidateResponse,
    CollectionScheduleResponse,
)
from lewisham_server.domain.errors import (
    AddressNotFoundError,
    CollectionScheduleNotFoundError,
    InvalidAddressSearchError,
    InvalidUprnError,
    UpstreamScraperChangedError,
    UpstreamUnavailableError,
)

router = APIRouter()


@router.get(
    "/addresses",
    response_model=list[AddressCandidateResponse],
    summary="Find Lewisham addresses",
)
async def lookup_addresses(
    postcode: Annotated[
        str,
        Query(
            description=(
                "Lewisham postcode or street text to resolve through the council "
                "address finder."
            ),
            examples=["SE6 1SQ"],
        ),
    ],
    service: BinsServiceDependency,
) -> list[AddressCandidateResponse]:
    """Return candidate UPRNs for a Lewisham postcode or street search."""

    try:
        addresses = await service.lookup_addresses(postcode)
    except InvalidAddressSearchError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except UpstreamScraperChangedError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
    except UpstreamUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    return [AddressCandidateResponse.from_domain(address) for address in addresses]


@router.get(
    "/addresses/{uprn}/collections",
    response_model=CollectionScheduleResponse,
    summary="Get a bin collection schedule",
)
async def get_collection_schedule(
    uprn: Annotated[
        str,
        Path(
            description="Unique Property Reference Number for a Lewisham address.",
            examples=["100000000001"],
        ),
    ],
    service: BinsServiceDependency,
) -> CollectionScheduleResponse:
    """Return the parsed collection schedule for one Lewisham address UPRN."""

    try:
        schedule = await service.get_collection_schedule(uprn)
    except InvalidUprnError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except (AddressNotFoundError, CollectionScheduleNotFoundError) as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except UpstreamScraperChangedError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
    except UpstreamUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    return CollectionScheduleResponse.from_domain(schedule)
