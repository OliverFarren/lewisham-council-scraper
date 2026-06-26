from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from datetime import timedelta

from fastapi import FastAPI

from lewisham_server.clients.lewisham import LewishamClient
from lewisham_server.services import BinsService
from lewisham_server.settings import Settings

Lifespan = Callable[[FastAPI], AbstractAsyncContextManager[None]]


def create_lifespan(settings: Settings) -> Lifespan:
    """Create the FastAPI lifespan handler for app-scoped dependencies."""

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        bins_service = _create_bins_service(settings)
        app.state.settings = settings
        app.state.bins_service = bins_service
        try:
            yield
        finally:
            await bins_service.aclose()

    return lifespan


def _create_bins_service(settings: Settings) -> BinsService:
    """Build the bins service with environment-driven upstream and cache policy."""

    client = LewishamClient(
        base_url=settings.upstream_base_url,
        collection_page_url=settings.upstream_collection_page_url,
        rounds_information_item_guid=settings.upstream_rounds_information_item_guid,
        user_agent=settings.upstream_user_agent,
        timeout_seconds=settings.upstream_request_timeout_seconds,
    )
    return BinsService(
        client=client,
        schedule_cache_ttl=timedelta(seconds=settings.cache_schedule_ttl_seconds),
        address_cache_ttl=timedelta(seconds=settings.cache_address_ttl_seconds),
        negative_cache_ttl=timedelta(seconds=settings.cache_negative_ttl_seconds),
    )
