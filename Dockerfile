# Production image for Timeweb Cloud Apps (build context = repository root).
# language=docker, empty build/run commands. EXPOSE selects the listen port.
FROM python:3.13-slim

WORKDIR /app

# Timeweb Apps probes /health with curl inside the container. Slim does not ship it.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.12.8 /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

COPY pyproject.toml uv.lock README.md ./
COPY src ./src

RUN uv sync --frozen --no-dev

# GET /health on 8080. Do not add HEALTHCHECK — a Dockerfile probe overrides the Apps panel.
EXPOSE 8080
CMD ["alice-gateway"]
