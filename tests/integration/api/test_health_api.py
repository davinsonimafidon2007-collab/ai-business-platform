"""Tests de integración del health compuesto (DEVOPS-001 / P3-002).

Requiere una base PostgreSQL disponible (misma DATABASE_URL que CI). El
health `/health` debe responder 200 y reportar checks de api/database/redis.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@pytest.mark.integration_db
def test_health_composite_returns_200_and_checks() -> None:
    """GET /health → 200 con checks de api/database/redis."""
    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["checks"]["api"] == "ok"
    assert body["checks"]["database"] == "ok"
    assert body["checks"]["redis"] in ("ok", "disabled", "error")
    assert "version" in body
    assert isinstance(body["providers"], list)


@pytest.mark.integration_db
def test_health_api_v1_also_reports_checks() -> None:
    """GET /api/v1/health mantiene el mismo contrato compuesto."""
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    body = response.json()
    assert "checks" in body
    assert "database" in body["checks"]
