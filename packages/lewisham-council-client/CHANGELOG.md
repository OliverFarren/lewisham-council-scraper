# Changelog

All notable changes to `lewisham-council-client` are documented here.

## Unreleased

## 0.3.0

### Changed

- Replaced the client's direct structlog dependency with named standard-library
  loggers so embedding applications retain control of filtering, formatting,
  and output.
- Client cache, request, completion, and pre-exception diagnostics are now
  `DEBUG` records. Applications remain responsible for visible operational
  events when they handle a result or typed exception.
- `UpstreamUnavailableError` raised for a timeout or transport failure now
  carries a `ContractDriftDiagnostics` snapshot with `endpoint`, `duration_ms`,
  and `error_type`, so a host can report those details without needing
  `DEBUG`-level access to the client's internal trace.
- Renamed the client's debug-level contract-drift event from
  `upstream_contract_drift` to `upstream_contract_drift_detected` so it no
  longer shares an event name with the server's application-level
  `upstream_contract_drift` event emitted at `ERROR`.

## 0.2.0

### Added

- `ContractDriftDiagnostics`, a structured, returnable snapshot of an
  upstream contract-drift failure (`source`, `payload_size_bytes`,
  `payload_sha256`, an opt-in `payload_preview`, `status_code`, `endpoint`).
  `source` (`"client"` or `"parser"`) tells a consumer which of the other
  fields to expect without needing to sniff which are non-`None`.
- `DomainError` (the base of every exception this package raises) now
  exposes a `diagnostics: ContractDriftDiagnostics | None` attribute,
  populated automatically by `LewishamParser` and `LewishamClient` when a
  drift failure occurs and `None` otherwise. Because it lives on the base
  class, callers can access `error.diagnostics` on any caught `DomainError`
  without needing to know the concrete subtype.
- `find_diagnostics(error)`, a public helper that walks an exception's
  `__cause__`/`__context__` chain for the first attached
  `ContractDriftDiagnostics`. Saves a consumer that wraps our exceptions in
  its own type — whether via explicit `raise SomeError(...) from err` or a
  bare `raise SomeError(...)` inside an `except` block — from reimplementing
  the chain walk.
- `CollectionSchedule.data_quality()`, returning a `DataQualitySummary`
  (counts of published vs. weekday-derived vs. missing `next_collection`
  entries). Lets a consumer build a data-quality report without duplicating
  knowledge of the `next_collection_basis` literal values.

### Changed

- `LewishamParser`'s raw-payload preview is now available on the returned
  diagnostics object as soon as the caller opts in via
  `include_raw_upstream=True`, independent of the standard-library logger
  level. Logging behaviour is unchanged: the `parser_contract_drift` log
  event still only includes the preview when the module logger is also at
  `DEBUG`.
- A freshly-parsed `CollectionScheduleNotFoundError` (a schedule with zero
  entries) still gets `diagnostics` attached, but is now logged as a
  `WARNING`-level `parser_schedule_empty` event rather than the `ERROR`-level
  `parser_contract_drift` event, since the parser cannot tell a genuinely
  empty schedule apart from one hollowed out by drift and the latter event
  name is reserved for failures it is confident are drift.
- `LewishamClient` now attaches `ContractDriftDiagnostics` at every
  `UpstreamScraperChangedError` it raises, not only for an unexpected HTTP
  status — malformed/non-JSON responses and shape-invalid `AddressFinder`
  items get diagnostics too.

## 0.1.0

Initial release.
