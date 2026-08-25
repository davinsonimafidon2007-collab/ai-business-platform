"""Tests unitarios del endpoint de salud compuesto (DEVOPS-001 / P3-002).

Cubre los estados del nuevo /health:
- ok       → API + DB ok, Redis ok (200)
- degraded → API + DB ok, Redis error/disabled (200)
- error    → DB down (503)
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@pytest.mark.asyncio
async def test_health_ok_all_checks() -> None:
    """DB ok + Redis ok → status 'ok', 200."""
    redis_client = MagicMock()
    redis_client.ping = AsyncMock(return_value=True)

    with patch(
        "app.api.v1.routes.health._check_database",
        new=AsyncMock(return_value=True),
    ), patch(
        "app.api.v1.routes.health._check_redis",
        new=AsyncMock(return_value="ok"),
    ):
        response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["checks"]["api"] == "ok"
    assert body["checks"]["database"] == "ok"
    assert body["checks"]["redis"] == "ok"
    assert "version" in body
    assert isinstance(body["providers"], list)


@pytest.mark.asyncio
async def test_health_redis_disabled_degraded() -> None:
    """DB ok + Redis no inicializado → status 'degraded', 200, redis='disabled'."""
    with patch(
        "app.api.v1.routes.health._check_database",
        new=AsyncMock(return_value=True),
    ), patch(
        "app.api.v1.routes.health._check_redis",
        new=AsyncMock(return_value="disabled"),
    ):
        response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "degraded"
    assert body["checks"]["database"] == "ok"
    assert body["checks"]["redis"] == "disabled"


@pytest.mark.asyncio
async def test_health_redis_down_degraded() -> None:
    """DB ok + Redis PING falla → status 'degraded', 200, redis='error'."""
    with patch(
        "app.api.v1.routes.health._check_database",
        new=AsyncMock(return_value=True),
    ), patch(
        "app.api.v1.routes.health._check_redis",
        new=AsyncMock(return_value="error"),
    ):
        response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "degraded"
    assert body["checks"]["redis"] == "error"


@pytest.mark.asyncio
async def test_health_database_down_error() -> None:
    """DB down → status 'error', 503, database='error'."""
    with patch(
        "app.api.v1.routes.health._check_database",
        new=AsyncMock(return_value=False),
    ), patch(
        "app.api.v1.routes.health._check_redis",
        new=AsyncMock(return_value="ok"),
    ):
        response = client.get("/health")

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "error"
    assert body["checks"]["database"] == "error"


@pytest.mark.asyncio
async def test_health_db_down_redis_error() -> None:
    """DB down + Redis down → status 'error', 503 (DB es el que tumba)."""
    with patch(
        "app.api.v1.routes.health._check_database",
        new=AsyncMock(return_value=False),
    ), patch(
        "app.api.v1.routes.health._check_redis",
        new=AsyncMock(return_value="error"),
    ):
        response = client.get("/health")

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "error"
    assert body["checks"]["database"] == "error"
    assert body["checks"]["redis"] == "error"


@pytest.mark.asyncio
async def test_health_exposes_es_data_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """TASK 1: /health expone es_data_mode para el banner de la UI."""
    from app.core.config import settings

    monkeypatch.setattr(settings, "es_data_mode", "fixture")

    with patch(
        "app.api.v1.routes.health._check_database",
        new=AsyncMock(return_value=True),
    ), patch(
        "app.api.v1.routes.health._check_redis",
        new=AsyncMock(return_value="ok"),
    ):
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["es_data_mode"] == "fixture"


@pytest.mark.asyncio
async def test_health_live_always_ok() -> None:
    """Liveness (TASK-004): /health/live responde 200 sin tocar DB/Redis."""
    # No se parchean _check_database/_check_redis a propósito: el liveness no
    # debe consultar dependencias, así que /health/live funciona incluso con
    # DB/Redis caídos.
    response = client.get("/health/live")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["checks"]["api"] == "ok"


@pytest.mark.asyncio
async def test_health_live_registered_in_api_prefix() -> None:
    """/api/v1/health/live también existe (mismo router montado en raíz)."""
    response = client.get("/api/v1/health/live")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


# ---------------------------------------------------------------------------
# /health/ready (readiness por TCP probe a DATABASE_URL/REDIS_URL)
# ---------------------------------------------------------------------------


def test_health_ready_ok_when_dependencies_listen(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """DB y Redis aceptan conexiones TCP → status 'ok' con ambos checks true."""
    import socket

    from app.api.v1.routes import health as health_module

    # Socket real en un puerto efímero: simula un servicio escuchando.
    # Backlog >= 2: el probe hace dos conexiones sin accept() intermedio y el
    # kernel debe completar el handshake de ambas.
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen(8)
    port = listener.getsockname()[1]
    try:
        monkeypatch.setattr(
            health_module, "_db_host_port", lambda: ("127.0.0.1", port)
        )
        monkeypatch.setattr(
            health_module, "_redis_host_port", lambda: ("127.0.0.1", port)
        )
        response = client.get("/health/ready")
    finally:
        listener.close()

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["db"] is True
    assert body["redis"] is True


def test_health_ready_degraded_when_nothing_listens(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Nada escuchando en los puertos → 'degraded', sin lanzar excepción."""
    from app.api.v1.routes import health as health_module

    # Puertos efímeros casi seguro libres; si algo escuchara, el test seguiría
    # siendo válido (ok != degraded solo si AMBOS fallan, improbable).
    monkeypatch.setattr(health_module, "_db_host_port", lambda: ("127.0.0.1", 1))
    monkeypatch.setattr(health_module, "_redis_host_port", lambda: ("127.0.0.1", 1))

    response = client.get("/health/ready")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "degraded"
    assert body["db"] is False
    assert body["redis"] is False


def test_health_ready_hosts_derived_from_settings_urls() -> None:
    """_host_port_from_url parsea esquemas con driver (postgresql+asyncpg)."""
    from app.api.v1.routes.health import _host_port_from_url

    host, port = _host_port_from_url(
        "postgresql+asyncpg://user:pass@db.internal:5433/appdb", 5432
    )
    assert (host, port) == ("db.internal", 5433)

    host, port = _host_port_from_url("redis://cache:6380/2", 6379)
    assert (host, port) == ("cache", 6380)

    # URL rota → fallback seguro a localhost + puerto por defecto.
    host, port = _host_port_from_url("", 5432)
    assert (host, port) == ("localhost", 5432)

