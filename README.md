# lewisham-council-scraper

[![CI](https://github.com/OliverFarren/lewisham-council-scraper/actions/workflows/ci.yml/badge.svg)](https://github.com/OliverFarren/lewisham-council-scraper/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/OliverFarren/lewisham-council-scraper/branch/main/graph/badge.svg)](https://codecov.io/gh/OliverFarren/lewisham-council-scraper)
[![Python](https://img.shields.io/badge/Python-3.12%20%7C%203.13%20%7C%203.14-3776AB?logo=python&logoColor=white)](https://www.python.org/)

A monorepo for accessing Lewisham Council civic data. The core is a reusable
Python client that speaks directly to Lewisham's undocumented HTTP endpoints.
A FastAPI adapter is an optional layer on top.

## Architecture

Lewisham's waste collection pages are backed by stateless HTTP endpoints that
require no browser, cookies, or authentication. That makes the scraper light
enough to embed in another Python application, which removes the need for a
separate service as a prerequisite for every consumer.

```
lewisham-council-client          ← reusable Python client (HTTP, parsing, domain models)
    ├── lewisham-server  ← optional FastAPI adapter (REST API, Docker image)
    └── (Home Assistant) ← planned: custom integration using the client directly
```

## Structure

```
lewisham-council-scraper/
├── packages/
│   ├── lewisham-council-client/   # Framework-neutral Python client (the core)
│   └── lewisham-server/   # FastAPI REST adapter
├── docs/                  # Design documents and spike findings
├── .github/
│   └── workflows/
│       ├── ci.yml         # Lint, typecheck, test on push/PR
│       └── publish.yml    # Publish lewisham-council-client to PyPI on tag
├── pyproject.toml         # uv workspace root
└── .python-version        # Python version pin
```

## Packages

### lewisham-council-client

The reusable core. Provides asynchronous address resolution and waste
collection schedule retrieval for any Lewisham UPRN. Has no dependency on
FastAPI, Home Assistant, MCP, or any web framework.

See [`packages/lewisham-council-client/README.md`](packages/lewisham-council-client/README.md).

### lewisham-server

FastAPI REST API that exposes the client over HTTP. Useful when a non-Python
consumer needs the data, or when several independent processes should share one
upstream cache. Distributed as a Docker image.

See [`packages/lewisham-server/README.md`](packages/lewisham-server/README.md).

## Development

Python 3.12 or later is supported. Install
[uv](https://docs.astral.sh/uv/), then use the top-level Makefile:

```bash
make install      # install all workspace packages and dev dependencies
make check        # lint, format check, typecheck, test (all packages)
make server-dev   # run the API server with hot reload
```

`make check` measures branch coverage across both packages and requires at
least 90%.

Focused commands:

```bash
make lint
make format
make typecheck-client
make typecheck-server
make test-client
make test-server
```

## Docker

```bash
make docker-build-server
```

Or directly:

```bash
docker build -f packages/lewisham-server/Dockerfile -t lewisham-server .
```
