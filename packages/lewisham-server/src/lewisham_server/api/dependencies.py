from collections.abc import AsyncIterator
from typing import Annotated, cast

from fastapi import Depends, Request

from lewisham_server.services import BinsService


async def get_bins_service(request: Request) -> AsyncIterator[BinsService]:
    """Yield the app-lifecycle bins service stored on FastAPI application state."""

    service = getattr(request.app.state, "bins_service", None)
    if service is None:
        raise RuntimeError("BinsService has not been initialised on app state.")

    yield cast(BinsService, service)


BinsServiceDependency = Annotated[BinsService, Depends(get_bins_service)]
