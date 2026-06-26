# Repository Guidance

This repository is a Python monorepo for scraping and serving Lewisham Council
data. Treat it as public FOSS infrastructure: clear code, explicit boundaries,
and tests that document behavior.

## Architecture

- `packages/lewisham-server` is the FastAPI REST service.
- `packages/lewisham-mcp` is the optional MCP wrapper around the REST service.
- Keep concerns separated:
  - `api/` owns FastAPI routes, dependencies, app assembly, and response schemas.
  - `services/` owns business orchestration and cache policy.
  - `clients/` owns outbound source-specific HTTP and parsing.
  - `domain/` owns pure models and domain errors.
  - `storage/` owns generic infrastructure such as caches.
- Do not add browser automation to production scraping unless direct HTTP is no
  longer viable and the change is explicitly justified.

## Engineering Standards

- Prefer boring, explicit Python over clever abstractions.
- Use strict typing and domain-specific exceptions.
- Do not introduce placeholder code, broad `except Exception` blocks, or TODOs.
- Keep lower-level signatures context-agnostic. For example, cache APIs should
  speak in keys, values, and TTLs, not bin schedules.
- Treat residential addresses, UPRNs, and raw traces as sensitive operational
  data. Do not commit real residential UPRNs or personal address fixtures.
- Add docstrings where they explain intent, lifecycle, public interfaces, or
  non-obvious source behavior. Avoid docstrings that merely restate names.

## Commands

Use the top-level `Makefile` for the standard workflow:

```bash
make install
make check
make server-dev
```

Useful focused commands:

```bash
make lint
make format-check
make typecheck-server
make test-server
make docker-build-server
```

The service Docker image should remain suitable for public self-hosting:

- Run as a non-root user.
- Configure runtime behavior through environment variables.
- Prefer namespaced service variables with the `LEWISHAM_SERVER_` prefix.
- Support common platform conventions such as `PORT`.

## Testing

- Do not make live network calls in tests.
- Mock Lewisham HTTP traffic at the `httpx` boundary.
- Keep fixtures local to a test file until they are genuinely reused.
- Parser tests should cover malformed upstream shape, empty schedules,
  non-breaking-space normalization, and date/frequency parsing.
- API tests should assert public HTTP behavior and error mapping, not private
  implementation details.

## Git Hygiene

- Do not revert unrelated user changes.
- Keep changes scoped to the requested package or behavior.
- Commit `uv.lock` for this application repo; Docker builds use frozen installs.
