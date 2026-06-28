from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, status

from lewisham_server.api.dependencies import LewishamServiceDependency
from lewisham_server.api.schemas.bins import CollectionScheduleResponse
from lewisham_server.domain.errors import (
    AddressNotFoundError,
    CollectionScheduleNotFoundError,
    InvalidUprnError,
    UpstreamScraperChangedError,
    UpstreamUnavailableError,
)

router = APIRouter()


@router.get(
    "/{uprn}/collections",
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
    service: LewishamServiceDependency,
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
