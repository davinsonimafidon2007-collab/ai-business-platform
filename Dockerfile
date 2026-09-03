# TASK 8 (AUD-027): build multi-stage.
#   - builder: instala dependencias (incluye toolchain de uv).
#   - runtime: solo el venv + el código, sin dependencias de desarrollo
#     (pytest/ruff ya no viajan a la imagen de ejecución) y con usuario
#     no-root.
FROM python:3.13-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:0.11.32 /uv /uvx /bin/

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH=/opt/venv/bin:$PATH

WORKDIR /app

COPY pyproject.toml uv.lock ./

# Solo dependencias de runtime: sin --group dev.
RUN uv sync --no-group dev


FROM python:3.13-slim AS runtime

COPY --from=ghcr.io/astral-sh/uv:0.11.32 /uv /uvx /bin/

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH=/opt/venv/bin:$PATH

# curl para el healthcheck del compose.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Usuario sin privilegios (antes el proceso corría como root).
RUN useradd --create-home --uid 10001 appuser

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY . .

# El directorio de subidas debe ser escribible por el usuario no-root.
RUN mkdir -p /app/uploads/inspection_photos \
    && chown -R appuser:appuser /app /opt/venv

USER appuser

EXPOSE 8000

CMD ["uv", "run", "--no-sync", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
