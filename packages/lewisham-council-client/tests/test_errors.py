"""Tests for domain error diagnostics attachment and chain-walking."""

from __future__ import annotations

from lewisham_client.domain.errors import (
    AddressNotFoundError,
    CollectionScheduleNotFoundError,
    InvalidUprnError,
    UpstreamScraperChangedError,
    find_diagnostics,
)
from lewisham_client.domain.models import ContractDriftDiagnostics


def _diagnostics() -> ContractDriftDiagnostics:
    return ContractDriftDiagnostics(
        error_type="UpstreamScraperChangedError",
        error_message="roundsinformation returned invalid JSON.",
        source="client",
    )


def test_domain_error_diagnostics_defaults_to_none_on_every_subclass() -> None:
    """diagnostics defaults to None even for subclasses that never populate it."""
    assert InvalidUprnError("UPRN must be non-empty.").diagnostics is None
    assert AddressNotFoundError("No address found for UPRN 1.").diagnostics is None


def test_domain_error_diagnostics_is_settable_via_constructor() -> None:
    diagnostics = _diagnostics()
    error = UpstreamScraperChangedError("bad response", diagnostics=diagnostics)
    assert error.diagnostics is diagnostics


def test_find_diagnostics_returns_none_for_plain_exception() -> None:
    assert find_diagnostics(ValueError("boom")) is None


def test_find_diagnostics_finds_diagnostics_on_the_error_itself() -> None:
    diagnostics = _diagnostics()
    error = CollectionScheduleNotFoundError("no entries", diagnostics=diagnostics)
    assert find_diagnostics(error) is diagnostics


def test_find_diagnostics_walks_the_cause_chain() -> None:
    """Mirrors a consumer explicitly re-raising via `raise ... from err`."""
    diagnostics = _diagnostics()
    original = UpstreamScraperChangedError("bad response", diagnostics=diagnostics)
    try:
        raise RuntimeError("wrapped") from original
    except RuntimeError as wrapped:
        assert find_diagnostics(wrapped) is diagnostics


def test_find_diagnostics_walks_the_context_chain() -> None:
    """A bare re-raise without `from err` still chains via __context__."""
    diagnostics = _diagnostics()
    original = UpstreamScraperChangedError("bad response", diagnostics=diagnostics)
    try:
        try:
            raise original
        except UpstreamScraperChangedError:
            raise RuntimeError("wrapped")  # noqa: B904 - implicit chaining is the point
    except RuntimeError as wrapped:
        assert find_diagnostics(wrapped) is diagnostics


def test_find_diagnostics_honours_suppressed_context() -> None:
    """`raise ... from None` is a deliberate signal to stop the chain walk."""
    diagnostics = _diagnostics()
    original = UpstreamScraperChangedError("bad response", diagnostics=diagnostics)
    try:
        try:
            raise original
        except UpstreamScraperChangedError:
            raise RuntimeError("wrapped") from None
    except RuntimeError as wrapped:
        assert find_diagnostics(wrapped) is None


def test_find_diagnostics_stops_at_a_cause_cycle_without_looping_forever() -> None:
    a = RuntimeError("a")
    b = RuntimeError("b")
    a.__cause__ = b
    b.__cause__ = a  # artificial cycle

    assert find_diagnostics(a) is None
