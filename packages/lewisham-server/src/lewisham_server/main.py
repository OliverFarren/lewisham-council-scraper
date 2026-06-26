"""ASGI entrypoint for uvicorn and other ASGI servers."""

from lewisham_server.api.app import create_app
from lewisham_server.logging_config import configure_logging
from lewisham_server.settings import get_settings

settings = get_settings()
configure_logging(settings)
app = create_app(settings)
