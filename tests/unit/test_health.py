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
async def test_health_ready_ok_all_checks() -> None:
    """DB ok + Redis ok → status 'ok', 200 (TASK 7)."""
    with patch(
        "app.api.v1.routes.health._check_database",
        new=AsyncMock(return_value=True),
    ), patch(
        "app.api.v1.routes.health._check_redis",
        new=AsyncMock(return_value="ok"),
    ):
        response = client.get("/health/ready")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["db"] is True
    assert body["redis"] is True


@pytest.mark.asyncio
async def test_health_ready_redis_disabled_still_ready() -> None:
    """DB ok + Redis no configurado (opcional) → sigue 'ok', 200 (TASK 7).

    Redis "disabled" es un estado soportado deliberadamente, no un fallo:
    un despliegue sin Redis configurado no debe quedar en 'degraded' para
    siempre.
    """
    with patch(
        "app.api.v1.routes.health._check_database",
        new=AsyncMock(return_value=True),
    ), patch(
        "app.api.v1.routes.health._check_redis",
        new=AsyncMock(return_value="disabled"),
    ):
        response = client.get("/health/ready")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["redis"] is True


@pytest.mark.asyncio
async def test_health_ready_redis_error_not_ready() -> None:
    """DB ok + Redis configurado pero caído → 'degraded', 500 (TASK 7)."""
    with patch(
        "app.api.v1.routes.health._check_database",
        new=AsyncMock(return_value=True),
    ), patch(
        "app.api.v1.routes.health._check_redis",
        new=AsyncMock(return_value="error"),
    ):
        response = client.get("/health/ready")

    assert response.status_code == 500
    body = response.json()
    assert body["status"] == "degraded"
    assert body["db"] is True
    assert body["redis"] is False


@pytest.mark.asyncio
async def test_health_ready_database_down_not_ready() -> None:
    """DB down → 'degraded', 500 — el código HTTP refleja el fallo (TASK 7)."""
    with patch(
        "app.api.v1.routes.health._check_database",
        new=AsyncMock(return_value=False),
    ), patch(
        "app.api.v1.routes.health._check_redis",
        new=AsyncMock(return_value="ok"),
    ):
        response = client.get("/health/ready")

    assert response.status_code == 500
    body = response.json()
    assert body["status"] == "degraded"
    assert body["db"] is False


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
# /health/ready — ver también los tests TASK 7 más abajo (test_health_ready_*):
# reutilizan _check_database()/_check_redis() (chequeo funcional real, no un
# TCP probe a DATABASE_URL/REDIS_URL) — decisión tomada al fusionar con
# origin/main, que sí tenía un TCP probe (_db_host_port/_redis_host_port/
# _host_port_from_url, ya eliminados junto con sus tests).
# ---------------------------------------------------------------------------

