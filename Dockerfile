# Production image (build context = repository root).
# The API key is a runtime environment variable, not a build argument.
FROM python:3.13-slim

WORKDIR /app

# The host probes /health with curl inside the container. Slim does not ship it.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.12.8 /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

COPY pyproject.toml uv.lock README.md ./
COPY src ./src
COPY prompts ./prompts

RUN uv sync --frozen --no-dev

# GET /health on 8080. Do not add HEALTHCHECK — a Dockerfile probe overrides the Apps panel.
EXPOSE 8080
CMD ["alice-gateway"]
