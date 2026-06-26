# lewisham-council-scraper

A monorepo for scraping and serving Lewisham Council data.

## Structure

```
lewisham-council-scraper/
├── packages/
│   ├── lewisham-server/   # FastAPI application exposing council data
│   └── lewisham-mcp/      # MCP server backed by lewisham-server
├── .github/
│   └── workflows/
│       ├── ci.yml         # Lint, typecheck, test on push/PR
│       └── publish.yml    # Publish Docker images to ghcr.io on tag
├── pyproject.toml         # uv workspace root
└── .python-version        # Python version pin
```

## Packages

### lewisham-server

FastAPI application that scrapes and serves Lewisham Council data via a REST API.

- `GET /bins/addresses?postcode={postcode}` - address candidates for a bin lookup
- `GET /bins/addresses/{uprn}/collections` - bin collection schedule for one UPRN

Configuration is environment-driven. Service-specific variables use the
`LEWISHAM_SERVER_` prefix; `PORT` is also accepted because many container
platforms provide it automatically.

| Variable | Default | Purpose |
| --- | --- | --- |
| `LEWISHAM_SERVER_HOST` | `0.0.0.0` | Bind host used by the bundled uvicorn runner. |
| `LEWISHAM_SERVER_PORT` | `8000` | Bind port. Takes precedence over `PORT`. |
| `PORT` | `8000` | Common platform port fallback. |
| `LEWISHAM_SERVER_WORKERS` | `1` | Number of uvicorn worker processes. |
| `LEWISHAM_SERVER_LOG_LEVEL` | `info` | Uvicorn log level. |
| `LEWISHAM_SERVER_UPSTREAM_BASE_URL` | `https://lewisham.gov.uk` | Lewisham upstream origin. |
| `LEWISHAM_SERVER_UPSTREAM_COLLECTION_PAGE_URL` | Lewisham bin collection page | Public page that backs the scraped endpoint. |
| `LEWISHAM_SERVER_UPSTREAM_ROUNDS_INFORMATION_ITEM_GUID` | Sitecore item GUID from the spike | Sitecore rendering ID used by the rounds-information endpoint. |
| `LEWISHAM_SERVER_UPSTREAM_USER_AGENT` | `lewisham-council-scraper/0.1` | User-Agent sent to Lewisham. |
| `LEWISHAM_SERVER_UPSTREAM_REQUEST_TIMEOUT_SECONDS` | `10.0` | Outbound request timeout. |
| `LEWISHAM_SERVER_CACHE_SCHEDULE_TTL_SECONDS` | `86400` | Positive schedule cache TTL. |
| `LEWISHAM_SERVER_CACHE_ADDRESS_TTL_SECONDS` | `604800` | Address cache TTL. |
| `LEWISHAM_SERVER_CACHE_NEGATIVE_TTL_SECONDS` | `3600` | Negative cache TTL. |

### lewisham-mcp

MCP (Model Context Protocol) server that exposes lewisham-server data as tools for AI assistants.

## Development

Install [uv](https://docs.astral.sh/uv/), then:

```bash
# Install all workspace packages and their dev dependencies
uv sync --all-packages

# Run the API server
uv run --package lewisham-server uvicorn lewisham_server.main:app --reload

# Run the MCP server
uv run --package lewisham-mcp python -m lewisham_mcp.server

# Lint
uv run ruff check .
uv run ruff format .

# Type check (per package)
cd packages/lewisham-server && uv run mypy src/
cd packages/lewisham-mcp   && uv run mypy src/

# Test (per package)
cd packages/lewisham-server && uv run pytest
cd packages/lewisham-mcp   && uv run pytest
```

The same workflow is also available through the top-level `Makefile`:

```bash
make install
make check
make server-dev
```

## Docker

Each package has a Dockerfile built from the repo root:

```bash
docker build -f packages/lewisham-server/Dockerfile -t lewisham-server .
docker build -f packages/lewisham-mcp/Dockerfile    -t lewisham-mcp .
```
