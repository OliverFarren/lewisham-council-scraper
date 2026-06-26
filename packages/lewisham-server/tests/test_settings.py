import pytest
from pydantic import ValidationError

from lewisham_server.settings import Settings


def test_settings_accept_namespaced_port_before_platform_port(
    monkeypatch,
) -> None:
    monkeypatch.setenv("LEWISHAM_SERVER_PORT", "9001")
    monkeypatch.setenv("PORT", "8001")

    settings = Settings()

    assert settings.port == 9001


def test_settings_accept_platform_port(monkeypatch) -> None:
    monkeypatch.delenv("LEWISHAM_SERVER_PORT", raising=False)
    monkeypatch.setenv("PORT", "8001")

    settings = Settings()

    assert settings.port == 8001


def test_settings_use_namespaced_upstream_values(monkeypatch) -> None:
    monkeypatch.setenv("LEWISHAM_SERVER_UPSTREAM_BASE_URL", "https://example.test")
    monkeypatch.setenv("LEWISHAM_SERVER_CACHE_NEGATIVE_TTL_SECONDS", "120")

    settings = Settings()

    assert settings.upstream_base_url == "https://example.test"
    assert settings.cache_negative_ttl_seconds == 120


def test_settings_use_logging_defaults(monkeypatch) -> None:
    monkeypatch.delenv("LEWISHAM_SERVER_LOG_LEVEL", raising=False)
    monkeypatch.delenv("LEWISHAM_SERVER_LOG_FORMAT", raising=False)
    monkeypatch.delenv("LEWISHAM_SERVER_LOG_INCLUDE_RAW_UPSTREAM", raising=False)
    monkeypatch.delenv("LEWISHAM_SERVER_LOG_RAW_UPSTREAM_MAX_CHARS", raising=False)

    settings = Settings()

    assert settings.log_level == "info"
    assert settings.log_format == "text"
    assert settings.log_include_raw_upstream is False
    assert settings.log_raw_upstream_max_chars == 4096


def test_settings_accept_logging_values(monkeypatch) -> None:
    monkeypatch.setenv("LEWISHAM_SERVER_LOG_LEVEL", "debug")
    monkeypatch.setenv("LEWISHAM_SERVER_LOG_FORMAT", "json")
    monkeypatch.setenv("LEWISHAM_SERVER_LOG_INCLUDE_RAW_UPSTREAM", "true")
    monkeypatch.setenv("LEWISHAM_SERVER_LOG_RAW_UPSTREAM_MAX_CHARS", "128")

    settings = Settings()

    assert settings.log_level == "debug"
    assert settings.log_format == "json"
    assert settings.log_include_raw_upstream is True
    assert settings.log_raw_upstream_max_chars == 128


def test_settings_reject_invalid_log_format(monkeypatch) -> None:
    monkeypatch.setenv("LEWISHAM_SERVER_LOG_FORMAT", "xml")

    with pytest.raises(ValidationError):
        Settings()
