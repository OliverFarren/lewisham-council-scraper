from importlib.metadata import PackageNotFoundError, version

try:
    APP_VERSION: str = version("lewisham-server")
except PackageNotFoundError:
    APP_VERSION = "unknown"
