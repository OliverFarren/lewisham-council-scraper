from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from lewisham_server.api.dependencies import LewishamServiceDependency
from lewisham_server.api.schemas.addresses import AddressCandidateResponse
from lewisham_server.domain.errors import (
    InvalidAddressSearchError,
    UpstreamScraperChangedError,
    UpstreamUnavailableError,
)

router = APIRouter()


@router.get(
    "",
    response_model=list[AddressCandidateResponse],
    summary="Search addresses",
)
async def search_addresses(
    query: Annotated[
        str,
        Query(
            description="Postcode or street text to resolve to address candidates.",
            examples=["SE6 1SQ"],
        ),
    ],
    service: LewishamServiceDependency,
) -> list[AddressCandidateResponse]:
    """Return address candidates with UPRNs for a postcode or street search."""

    try:
        addresses = await service.lookup_addresses(query)
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
