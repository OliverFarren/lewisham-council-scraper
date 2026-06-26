# Build from the repo root:
#   docker build -f packages/lewisham-server/Dockerfile -t lewisham-server .
FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy workspace config and lock file first for layer caching
COPY pyproject.toml uv.lock* ./
COPY packages/lewisham-server/pyproject.toml packages/lewisham-server/

# Install only this package's production deps
RUN uv sync --frozen --no-dev --package lewisham-server

COPY packages/lewisham-server/src/ packages/lewisham-server/src/

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

CMD ["uvicorn", "lewisham_server.main:app", "--host", "0.0.0.0", "--port", "8000"]
