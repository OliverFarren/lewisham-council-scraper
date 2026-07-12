from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, status
from lewisham_client.domain.errors import (
    AddressNotFoundError,
    CollectionScheduleNotFoundError,
    InvalidUprnError,
    UpstreamScraperChangedError,
    UpstreamUnavailableError,
)

from lewisham_server.api.dependencies import LewishamServiceDependency
from lewisham_server.api.operational_logging import (
    log_contract_drift,
    log_parser_schedule_empty,
    log_schedule_lookup_completed,
    log_upstream_unavailable,
)
from lewisham_server.api.schemas.bins import CollectionScheduleResponse

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
    except AddressNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except CollectionScheduleNotFoundError as exc:
        log_parser_schedule_empty(exc)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except UpstreamScraperChangedError as exc:
        log_contract_drift(exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
    except UpstreamUnavailableError as exc:
        log_upstream_unavailable(exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    log_schedule_lookup_completed(
        collection_count=len(schedule.collections),
        source_url=schedule.source_url,
        fetched_at=schedule.fetched_at.isoformat(),
    )
    return CollectionScheduleResponse.from_domain(schedule)
