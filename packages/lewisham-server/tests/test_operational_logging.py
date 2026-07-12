import json

from lewisham_client.domain.errors import UpstreamScraperChangedError
from lewisham_client.domain.models import ContractDriftDiagnostics

from lewisham_server.api.operational_logging import log_contract_drift
from lewisham_server.logging_config import configure_logging
from lewisham_server.settings import Settings


def _drift_error() -> UpstreamScraperChangedError:
    return UpstreamScraperChangedError(
        "roundsinformation returned invalid JSON",
        diagnostics=ContractDriftDiagnostics(
            error_type="UpstreamScraperChangedError",
            error_message="roundsinformation returned invalid JSON",
            source="parser",
            payload_size_bytes=42,
            payload_sha256="abc123",
            payload_preview="SECRET-UPSTREAM-PAYLOAD",
            payload_truncated=True,
        ),
    )


def test_contract_drift_hides_raw_preview_at_info_level(capsys) -> None:
    configure_logging(Settings(log_format="json", log_level="info"))

    log_contract_drift(_drift_error())

    captured = capsys.readouterr()
    event = json.loads(captured.err)
    assert event["event"] == "upstream_contract_drift"
    assert event["payload_size_bytes"] == 42
    assert event["payload_sha256"] == "abc123"
    assert "payload_preview" not in event
    assert "SECRET-UPSTREAM-PAYLOAD" not in captured.err


def test_contract_drift_includes_opted_in_raw_preview_at_debug_level(capsys) -> None:
    configure_logging(Settings(log_format="json", log_level="debug"))

    log_contract_drift(_drift_error())

    captured = capsys.readouterr()
    event = json.loads(captured.err)
    assert event["payload_preview"] == "SECRET-UPSTREAM-PAYLOAD"
    assert event["payload_truncated"] is True
