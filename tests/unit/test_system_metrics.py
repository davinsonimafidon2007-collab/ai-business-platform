"""Tests unitarios del endpoint público /metrics (Bloque 6 / DEVOPS).

Verifica que /metrics expone el registry prometheus-style en formato
text/plain sin requerir autenticación (scraping de Prometheus interno).
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@pytest.mark.asyncio
async def test_metrics_returns_ok_without_auth() -> None:
    """/metrics responde 200 text/plain sin token (scraping interno)."""
    response = client.get("/metrics")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")


@pytest.mark.asyncio
async def test_metrics_contains_recorded_series() -> None:
    """Las métricas grabadas en el registry aparecen en la exposición."""
    from app.services.metrics_service import record_opportunity_generated, record_search_request

    record_search_request("autoscout24")
    record_search_request("autoscout24")
    record_opportunity_generated()

    response = client.get("/metrics")

    assert response.status_code == 200
    body = response.text
    assert '# TYPE search_requests_total counter' in body
    assert 'search_requests_total{provider="autoscout24"} 2' in body
    assert '# TYPE opportunities_generated_total counter' in body
    assert 'opportunities_generated_total 1' in body


@pytest.mark.asyncio
async def test_metrics_registered_in_api_prefix() -> None:
    """/api/v1/metrics también existe (mismo router montado en raíz)."""
    response = client.get("/api/v1/metrics")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")