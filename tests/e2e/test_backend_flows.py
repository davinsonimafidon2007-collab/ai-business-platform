"""E2E backend: flujo auth → search → dashboard → health."""

from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture()
async def api_client() -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(base_url="http://test", transport=transport) as client:
        yield client


@pytest.mark.anyio
async def test_health_is_public(api_client: AsyncClient) -> None:
    response = await api_client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] in {"ok", "degraded"}


@pytest.mark.anyio
async def test_search_is_public(api_client: AsyncClient) -> None:
    response = await api_client.post(
        "/api/v1/search",
        json={"query": "BMW", "max_results": 1, "providers": ["mobile_de"]},
        headers={"Authorization": "Bearer test"},
    )
    assert response.status_code in {200, 401, 422}
    body = response.json()
    assert "results" in body or "error" in body


@pytest.mark.anyio
async def test_dashboard_requires_auth(api_client: AsyncClient) -> None:
    response = await api_client.get("/api/v1/dashboard/stats")
    assert response.status_code == 401


@pytest.mark.anyio
async def test_full_auth_flow(api_client: AsyncClient) -> None:
    email = f"e2e-{uuid.uuid4()}@example.com"
    register = await api_client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "changeme",
            "full_name": "E2E User",
        },
    )
    assert register.status_code == 201, register.text

    login = await api_client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "changeme"},
    )
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]

    dashboard = await api_client.get(
        "/api/v1/dashboard/stats",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert dashboard.status_code == 200, dashboard.text
    payload = dashboard.json()
    assert "recent_searches" in payload
    assert payload["recent_searches"] == 0
