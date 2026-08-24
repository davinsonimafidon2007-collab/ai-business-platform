FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:0.11.32 /uv /uvx /bin/

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH=/opt/venv/bin:$PATH

WORKDIR /app

COPY pyproject.toml uv.lock ./

RUN uv sync --group dev

# Playwright browsers (chromium) para mobile.de headless — sin cuenta, solo
# se descarga si ENABLE_MOBILE_DE_PLAYWRIGHT=true en runtime. Instalación
# cacheable; no bloquea el boot si falla (fallback httpx).
RUN uv run --no-sync playwright install --with-deps chromium || echo "playwright browsers skip (offline)"

COPY . .

EXPOSE 8000

# Install curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

CMD ["uv", "run", "--no-sync", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

