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
    """Las métricas grabadas en el registry aparecen en la exposición.

    TEST.D fix (flaky): el registry de métricas es un singleton por proceso y
    otros tests también incrementan estos contadores; se compara contra el
    valor BASE en lugar de valores absolutos para no depender del orden.
    """
    import re

    from app.services.metrics_service import (
        metrics,
        record_opportunity_generated,
        record_search_request,
    )

    def _counter_value(body: str, pattern: str) -> float:
        match = re.search(pattern, body, flags=re.MULTILINE)
        return float(match.group(1)) if match else 0.0

    baseline = metrics.to_prometheus()
    base_search = _counter_value(
        baseline, r'search_requests_total\{provider="autoscout24"\} (\S+)'
    )
    base_opps = _counter_value(baseline, r"^opportunities_generated_total (\S+)$")

    record_search_request("autoscout24")
    record_search_request("autoscout24")
    record_opportunity_generated()

    response = client.get("/metrics")

    assert response.status_code == 200
    body = response.text
    assert "# TYPE search_requests_total counter" in body
    assert (
        _counter_value(body, r'search_requests_total\{provider="autoscout24"\} (\S+)')
        == base_search + 2
    )
    assert "# TYPE opportunities_generated_total counter" in body
    assert (
        _counter_value(body, r"^opportunities_generated_total (\S+)") == base_opps + 1
    )


@pytest.mark.asyncio
async def test_metrics_registered_in_api_prefix() -> None:
    """/api/v1/metrics también existe (mismo router montado en raíz)."""
    response = client.get("/api/v1/metrics")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")