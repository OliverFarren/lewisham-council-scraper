# Repository Guidance

This repository is a Python monorepo for retrieving and integrating Lewisham
Council data. Treat it as public FOSS infrastructure: clear code, explicit
boundaries, and tests that document behavior.

## Architecture

- Follow `docs/design_002_client_first_architecture.md` for the accepted target
  architecture and dependency direction.
- The reusable, framework-neutral Python client is the core capability.
- `packages/lewisham-server` is an optional FastAPI adapter. It currently
  contains code that will move into the client during the migration.
- `packages/lewisham-mcp` is an optional MCP adapter. Local MCP use should
  consume the client directly rather than require the REST service.
- A Home Assistant integration should consume the client directly and must not
  require users to deploy the REST service.
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

## Documentation

- Keep frontmatter `status` values current in the same change that completes,
  accepts, replaces, or abandons documented work.
- Use these lifecycle values consistently:
  - `draft`: actively being written and not ready for a decision.
  - `proposed`: ready for review but not yet adopted.
  - `accepted`: the current architectural or product direction.
  - `complete`: a finite investigation or work item has concluded.
  - `superseded`: replaced by a later document; preserve it as historical
    context and link to its successor.
  - `abandoned`: intentionally stopped without completion or replacement.
- Mark a spike plan `complete` when its investigation has concluded and link it
  to the corresponding findings.
- When a design changes, add a prominent successor link to the earlier document
  rather than rewriting the historical rationale.

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
