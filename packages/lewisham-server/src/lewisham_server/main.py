"""ASGI entrypoint for uvicorn and other ASGI servers."""

from lewisham_server._version import APP_VERSION
from lewisham_server.api.app import create_app
from lewisham_server.logging_config import configure_logging
from lewisham_server.settings import get_settings
from lewisham_server.startup_banner import print_startup_banner

settings = get_settings()
configure_logging(settings)
print_startup_banner(settings.log_format, app_version=APP_VERSION)
app = create_app(settings)
