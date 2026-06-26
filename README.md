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

- `GET /bins` — bin collection data (placeholder)

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

## Docker

Each package has a Dockerfile built from the repo root:

```bash
docker build -f packages/lewisham-server/Dockerfile -t lewisham-server .
docker build -f packages/lewisham-mcp/Dockerfile    -t lewisham-mcp .
```
