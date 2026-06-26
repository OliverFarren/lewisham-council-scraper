# Build from the repo root:
#   docker build -f packages/lewisham-mcp/Dockerfile -t lewisham-mcp .
FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy workspace config and lock file first for layer caching
COPY pyproject.toml uv.lock* ./
COPY packages/lewisham-mcp/pyproject.toml packages/lewisham-mcp/

# Install only this package's production deps
RUN uv sync --frozen --no-dev --package lewisham-mcp

COPY packages/lewisham-mcp/src/ packages/lewisham-mcp/src/

ENV PATH="/app/.venv/bin:$PATH"
ENV LEWISHAM_SERVER_URL="http://lewisham-server:8000"

CMD ["python", "-m", "lewisham_mcp.server"]
