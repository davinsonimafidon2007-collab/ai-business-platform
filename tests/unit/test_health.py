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

