from fastapi import FastAPI

from lewisham_server._version import APP_VERSION
from lewisham_server.api.lifespan import create_lifespan
from lewisham_server.api.middleware import add_request_logging_middleware
from lewisham_server.api.routers import addresses, bins
from lewisham_server.settings import APP_NAME, Settings, get_settings


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create the FastAPI application and its app-lifecycle dependencies."""

    app_settings = settings or get_settings()
    app = FastAPI(
        title=APP_NAME,
        version=APP_VERSION,
        lifespan=create_lifespan(app_settings),
    )
    add_request_logging_middleware(app)
    app.include_router(addresses.router, prefix="/addresses", tags=["addresses"])
    app.include_router(bins.router, prefix="/bins", tags=["bins"])
    return app
