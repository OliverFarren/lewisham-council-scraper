from fastapi import FastAPI

from lewisham_server.api.lifespan import create_lifespan
from lewisham_server.api.routers import bins
from lewisham_server.settings import Settings, get_settings


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create the FastAPI application and its app-lifecycle dependencies."""

    app_settings = settings or get_settings()
    app = FastAPI(
        title=app_settings.app_name,
        version=app_settings.app_version,
        lifespan=create_lifespan(app_settings),
    )
    app.include_router(bins.router, prefix="/bins", tags=["bins"])
    return app
