from collections.abc import AsyncIterator
from typing import Annotated, cast

from fastapi import Depends, Request
from lewisham_client.services import LewishamService


async def get_lewisham_service(request: Request) -> AsyncIterator[LewishamService]:
    """Yield the app-lifecycle Lewisham service stored on FastAPI application state."""

    service = getattr(request.app.state, "lewisham_service", None)
    if service is None:
        raise RuntimeError("LewishamService has not been initialised on app state.")

    yield cast(LewishamService, service)


LewishamServiceDependency = Annotated[LewishamService, Depends(get_lewisham_service)]
