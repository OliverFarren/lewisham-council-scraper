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
