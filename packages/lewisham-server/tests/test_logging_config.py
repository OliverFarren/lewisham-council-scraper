import json
import logging

import structlog

from lewisham_server.logging_config import configure_logging
from lewisham_server.settings import Settings


def test_json_logging_redacts_sensitive_fields_and_drops_unknown_fields(
    capsys,
) -> None:
    configure_logging(Settings(log_format="json", log_level="debug"))

    structlog.get_logger("test").info(
        "privacy_check",
        route="/bins/addresses/{uprn}/collections",
        uprn="100000000001",
        address="1 Example Street",
        ignored_field="not rendered",
    )

    captured = capsys.readouterr()
    event = json.loads(captured.out)

    assert event["event"] == "privacy_check"
    assert event["route"] == "/bins/addresses/{uprn}/collections"
    assert event["uprn_redacted"] is True
    assert event["address_redacted"] is True
    assert "100000000001" not in captured.out
    assert "1 Example Street" not in captured.out
    assert "ignored_field" not in event


def test_text_logging_splits_low_and_high_severity_streams(capsys) -> None:
    configure_logging(Settings(log_format="text", log_level="debug"))
    logger = structlog.get_logger("test")

    logger.debug("debug_event")
    logger.info("info_event")
    logger.warning("warning_event")

    captured = capsys.readouterr()

    assert "debug_event" in captured.out
    assert "info_event" in captured.out
    assert "warning_event" not in captured.out
    assert "warning_event" in captured.err


def test_uvicorn_access_logger_is_suppressed() -> None:
    configure_logging(Settings(log_format="json", log_level="info"))

    access_logger = logging.getLogger("uvicorn.access")

    assert access_logger.handlers == []
    assert access_logger.level == logging.CRITICAL
    assert access_logger.propagate is False
