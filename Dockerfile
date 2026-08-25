FROM python:3.13-slim

# Dependencias de sistema primero (capa estable, cacheable entre builds).
# curl se necesita para el HEALTHCHECK; los deps de Playwright para el
# provider opcional mobile.de (ENABLE_MOBILE_DE_PLAYWRIGHT=true en runtime).
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.11.32 /uv /uvx /bin/

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH=/opt/venv/bin:$PATH

WORKDIR /app

# Solo manifiestos primero: la capa de deps solo se invalida al cambiar el lock.
COPY pyproject.toml uv.lock ./

# --frozen: falla si uv.lock no coincide con pyproject.toml (nunca re-resuelve).
RUN uv sync --frozen --group dev

# Playwright browsers (chromium) para mobile.de headless — sin cuenta, solo
# se descarga si ENABLE_MOBILE_DE_PLAYWRIGHT=true en runtime. Instalación
# cacheable; no bloquea el boot si falla (fallback httpx).
RUN uv run --no-sync playwright install --with-deps chromium || echo "playwright browsers skip (offline)"

# Código al final: cualquier cambio de fuente reutiliza las capas anteriores.
COPY . .

# Non-root: el proceso no necesita privilegios. /app es propiedad del usuario
# de runtime para que uploads/ y volúmenes montados sean escribibles.
RUN groupadd --gid 1000 appgroup \
    && useradd --uid 1000 --gid appgroup --create-home appuser \
    && chown -R appuser:appgroup /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -fsS http://localhost:8000/health/live || exit 1

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
