# Build from the repo root:
#   docker build -f packages/lewisham-server/Dockerfile -t lewisham-server .
FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH" \
    LEWISHAM_SERVER_HOST="0.0.0.0" \
    PORT="8000"

# Copy workspace config and lock file first for layer caching
COPY pyproject.toml uv.lock* ./
COPY packages/lewisham-server/pyproject.toml packages/lewisham-server/

# Install only this package's production deps
RUN uv sync --frozen --no-dev --package lewisham-server --no-install-project

COPY packages/lewisham-server/src/ packages/lewisham-server/src/

RUN uv sync --frozen --no-dev --package lewisham-server \
    && groupadd --system --gid 10001 lewisham \
    && useradd \
        --system \
        --uid 10001 \
        --gid lewisham \
        --home-dir /app \
        --shell /usr/sbin/nologin \
        lewisham \
    && chown -R lewisham:lewisham /app

USER lewisham

EXPOSE 8000

CMD ["python", "-m", "lewisham_server"]
