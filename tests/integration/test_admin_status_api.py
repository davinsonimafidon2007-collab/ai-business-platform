"""Integration tests for admin system status endpoints (Tasks G.1 + G.2 + G.4).

G.1 — GET /api/v1/admin/status:
1. Sin auth → 401
2. USER → 403
3. ADMIN sin canary previo → 200, canary.success is null
4. ADMIN tras set_last_canary_result → 200 con success, mobile_status, bloques
5. redis_ok refleja ping si hay cliente Redis (mockeado)

G.2 — POST /api/v1/admin/status/canary:
6. Sin auth → 401
7. USER → 403
8. ADMIN con job mockeado success=True → 200, canary.success is True
9. ADMIN con job que deja success=False → 200 (FAIL de negocio ≠ 500)
10. Tras POST, GET refleja el mismo snapshot (estado compartido)

G.4 — jobs metrics en /api/v1/admin/status:
11. ADMIN con scheduler y 1 job (consecutive_failures=3) → 200, jobs[0] incluye racha
12. Sin scheduler (ENABLE_SCHEDULER=false) → 200 con jobs == []
13. POST canary devuelve el mismo shape (incluye jobs)
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.jobs import canary_state
from app.main import app
from app.models.role import Role
from tests.integration.conftest import user_repository


def _promote_to_admin(user_id: str) -> None:
    """Promueve el rol del usuario a ADMIN en el repo fake (sync)."""
    for user in user_repository._users.values():
        if str(user.id) == str(user_id):
            user.role = Role.ADMIN
            return
    raise AssertionError(f"User {user_id} not found in fake repo")


def _email() -> str:
    return f"adminstatus_{uuid.uuid4().hex[:12]}@example.com"


def _register(client: TestClient, *, role: Role = Role.USER) -> dict:
    """Registra un usuario y devuelve (user_id, token)."""
    email, password = _email(), "password123"
    r = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password},
    )
    assert r.status_code in (200, 201), r.text
    user_id = str(r.json()["id"])

    if role == Role.ADMIN:
        _promote_to_admin(user_id)

    login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200, login.text
    return {"user_id": user_id, "token": login.json()["access_token"]}


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def _reset_canary_state():
    """Limpia el holder del canary antes y después de cada test."""
    canary_state._last = None
    yield
    canary_state._last = None


class _FakeScheduler:
    """Fake scheduler con la misma API de ``Scheduler.list_jobs`` (G.4)."""

    def __init__(self, rows: list[dict]) -> None:
        self._rows = rows

    def list_jobs(self) -> list[dict]:
        return list(self._rows)


@pytest.fixture(autouse=True)
def _reset_scheduler_state():
    """Limpia ``app.state.scheduler`` antes y después de cada test (G.4).

    El test puede dejar un ``_FakeScheduler`` en ``app.state.scheduler``;
    al terminar lo restauramos al estado previo (o a ``None`` si no había).
    """
    had_scheduler = hasattr(app.state, "scheduler")
    prev = getattr(app.state, "scheduler", None)
    app.state.scheduler = None
    yield
    if had_scheduler:
        app.state.scheduler = prev
    else:
        app.state.scheduler = None


class TestJobMetrics:
    """Integration tests para jobs metrics en /admin/status (Task G.4)."""

    def test_admin_sees_job_metrics_with_streak(self, client: TestClient) -> None:
        admin = _register(client, role=Role.ADMIN)
        app.state.scheduler = _FakeScheduler(
            [
                {
                    "name": "refresh_market_cache",
                    "interval": 3600,
                    "status": "failed",
                    "last_execution": "2026-08-04T12:00:00Z",
                    "next_execution": "2026-08-04T13:00:00Z",
                    "last_duration": 1.5,
                    "execution_count": 10,
                    "success_count": 7,
                    "failure_count": 3,
                    "consecutive_failures": 3,
                }
            ]
        )

        r = client.get("/api/v1/admin/status", headers=_auth(admin["token"]))
        assert r.status_code == 200, r.text
        data = r.json()
        assert "jobs" in data
        assert len(data["jobs"]) == 1
        job = data["jobs"][0]
        assert job["name"] == "refresh_market_cache"
        assert job["interval"] == 3600
        assert job["status"] == "failed"
        assert job["last_execution"] == "2026-08-04T12:00:00Z"
        assert job["next_execution"] == "2026-08-04T13:00:00Z"
        assert job["last_duration"] == 1.5
        assert job["execution_count"] == 10
        assert job["success_count"] == 7
        assert job["failure_count"] == 3
        assert job["consecutive_failures"] == 3

    def test_no_scheduler_returns_empty_jobs(self, client: TestClient) -> None:
        admin = _register(client, role=Role.ADMIN)
        app.state.scheduler = None

        r = client.get("/api/v1/admin/status", headers=_auth(admin["token"]))
        assert r.status_code == 200, r.text
        assert r.json()["jobs"] == []

    def test_post_canary_includes_jobs(self, client: TestClient) -> None:
        admin = _register(client, role=Role.ADMIN)
        app.state.scheduler = _FakeScheduler(
            [
                {
                    "name": "cleanup_old_searches",
                    "interval": 86400,
                    "status": "success",
                    "last_execution": "2026-08-04T10:00:00Z",
                    "next_execution": "2026-08-05T10:00:00Z",
                    "last_duration": 0.5,
                    "execution_count": 5,
                    "success_count": 5,
                    "failure_count": 0,
                    "consecutive_failures": 0,
                }
            ]
        )

        fake_job = _FakeCanaryJob(
            success=True,
            message="Canary OK (AS24 listings>0, mobile=ok)",
            data={"autoscout24": {"count": 3}, "mobile_de": {"count": 2}, "mobile_status": "ok"},
        )
        with patch(
            "app.api.v1.admin_status.ProviderCanaryJob", return_value=fake_job
        ):
            r = client.post(
                "/api/v1/admin/status/canary", headers=_auth(admin["token"])
            )

        assert r.status_code == 200, r.text
        data = r.json()
        assert "jobs" in data
        assert len(data["jobs"]) == 1
        assert data["jobs"][0]["name"] == "cleanup_old_searches"
        assert data["jobs"][0]["consecutive_failures"] == 0


class TestAdminSystemStatus:
    def test_unauthenticated_401(self, client: TestClient) -> None:
        r = client.get("/api/v1/admin/status")
        assert r.status_code == 401

    def test_user_forbidden_403(self, client: TestClient) -> None:
        user = _register(client)
        r = client.get("/api/v1/admin/status", headers=_auth(user["token"]))
        assert r.status_code == 403

    def test_admin_no_canary_returns_empty(self, client: TestClient) -> None:
        admin = _register(client, role=Role.ADMIN)
        r = client.get("/api/v1/admin/status", headers=_auth(admin["token"]))
        assert r.status_code == 200, r.text
        data = r.json()
        assert "canary" in data
        assert data["canary"]["success"] is None
        assert data["canary"]["message"] is None
        assert data["canary"]["finished_at"] is None
        assert data["canary"]["autoscout24"] is None
        assert data["canary"]["mobile_de"] is None
        assert data["canary"]["strict_mobile"] is None
        assert data["canary"]["mobile_status"] is None

    def test_admin_with_canary_data(self, client: TestClient) -> None:
        admin = _register(client, role=Role.ADMIN)

        canary_data = {
            "autoscout24": {"count": 5, "sample_id": "as24-0", "sample_price": 1000},
            "mobile_de": {"count": 3},
            "strict_mobile": True,
            "mobile_status": "ok",
        }
        canary_state.set_last_canary_result(
            success=True,
            message="Canary OK (AS24 listings>0, mobile=ok)",
            data=canary_data,
        )

        r = client.get("/api/v1/admin/status", headers=_auth(admin["token"]))
        assert r.status_code == 200, r.text
        data = r.json()
        canary = data["canary"]
        assert canary["success"] is True
        assert canary["message"] == "Canary OK (AS24 listings>0, mobile=ok)"
        assert canary["finished_at"] is not None
        assert canary["autoscout24"] == {"count": 5, "sample_id": "as24-0", "sample_price": 1000}
        assert canary["mobile_de"] == {"count": 3}
        assert canary["strict_mobile"] is True
        assert canary["mobile_status"] == "ok"

    def test_admin_status_includes_providers_snapshot(self, client: TestClient) -> None:
        """ADMIN.1: /admin/status incluye providers + flags ES."""
        from app.core.config import settings
        from app.providers.registry import ProviderRegistry
        from app.schemas.admin_status import ProvidersStatus

        admin = _register(client, role=Role.ADMIN)
        ProviderRegistry.clear()
        ProviderRegistry.ensure_default_providers()

        try:
            r = client.get("/api/v1/admin/status", headers=_auth(admin["token"]))
            assert r.status_code == 200, r.text
            data = r.json()
            providers = data["providers"]
            assert isinstance(providers, dict)
            assert "providers" in providers
            assert "default_import_cost_profile" in providers
            assert "enable_es_market_fixture" in providers
            assert "enable_coches_net_fixture" in providers
            assert "enable_autoscout24_es" in providers

            ps = ProvidersStatus(**providers)
            assert isinstance(ps.providers, list)
            assert ps.default_import_cost_profile == settings.default_import_cost_profile
            assert ps.enable_es_market_fixture == settings.enable_es_market_fixture
            assert ps.enable_coches_net_fixture == settings.enable_coches_net_fixture
            assert ps.enable_autoscout24_es == settings.enable_autoscout24_es
        finally:
            ProviderRegistry.clear()

    def test_admin_with_failed_canary(self, client: TestClient) -> None:
        admin = _register(client, role=Role.ADMIN)

        canary_data = {
            "autoscout24": {"error": "ConnectionError"},
            "mobile_de": {"count": 0},
            "strict_mobile": False,
            "mobile_status": "empty",
        }
        canary_state.set_last_canary_result(
            success=False,
            message="Canary FAIL: AutoScout24 devolvió 0 listings o error",
            data=canary_data,
        )

        r = client.get("/api/v1/admin/status", headers=_auth(admin["token"]))
        assert r.status_code == 200, r.text
        canary = r.json()["canary"]
        assert canary["success"] is False
        assert "FAIL" in canary["message"]
        assert canary["mobile_status"] == "empty"
        assert canary["strict_mobile"] is False

    def test_redis_ok_true_when_ping_succeeds(self, client: TestClient) -> None:
        admin = _register(client, role=Role.ADMIN)

        mock_client = AsyncMock()
        mock_client.ping = AsyncMock(return_value=True)

        with patch("app.api.v1.admin_status.get_redis", return_value=mock_client):
            r = client.get("/api/v1/admin/status", headers=_auth(admin["token"]))

        assert r.status_code == 200
        assert r.json()["redis_ok"] is True

    def test_redis_ok_false_when_ping_fails(self, client: TestClient) -> None:
        admin = _register(client, role=Role.ADMIN)

        mock_client = AsyncMock()
        mock_client.ping = AsyncMock(side_effect=Exception("connection refused"))

        with patch("app.api.v1.admin_status.get_redis", return_value=mock_client):
            r = client.get("/api/v1/admin/status", headers=_auth(admin["token"]))

        assert r.status_code == 200
        assert r.json()["redis_ok"] is False

    def test_redis_ok_none_when_no_client(self, client: TestClient) -> None:
        admin = _register(client, role=Role.ADMIN)

        with patch("app.api.v1.admin_status.get_redis", return_value=None):
            r = client.get("/api/v1/admin/status", headers=_auth(admin["token"]))

        assert r.status_code == 200
        assert r.json()["redis_ok"] is None


class _FakeCanaryJob:
    """Fake que evita pegarle a mobile.de/AS24 en CI.

    En lugar de una red real, ejecuta el contrato del job: llama a
    ``set_last_canary_result`` y devuelve un ``JobResult``.
    """

    def __init__(self, success: bool, message: str, data: dict) -> None:
        self._success = success
        self._message = message
        self._data = data

    async def execute(self, context) -> None:
        from app.jobs.base import JobResult

        canary_state.set_last_canary_result(
            success=self._success,
            message=self._message,
            data=self._data,
        )
        return JobResult(success=self._success, message=self._message, data=self._data)


class TestRunProviderCanary:
    """Integration tests para POST /api/v1/admin/status/canary (Task G.2)."""

    def test_unauthenticated_401(self, client: TestClient) -> None:
        r = client.post("/api/v1/admin/status/canary")
        assert r.status_code == 401

    def test_user_forbidden_403(self, client: TestClient) -> None:
        user = _register(client)
        r = client.post("/api/v1/admin/status/canary", headers=_auth(user["token"]))
        assert r.status_code == 403

    def test_admin_success_job_returns_snapshot(self, client: TestClient) -> None:
        admin = _register(client, role=Role.ADMIN)

        fake_data = {
            "autoscout24": {"count": 7, "sample_id": "as24-1", "sample_price": 2500},
            "mobile_de": {"count": 4},
            "strict_mobile": True,
            "mobile_status": "ok",
        }
        fake_job = _FakeCanaryJob(
            success=True,
            message="Canary OK (AS24 listings>0, mobile=ok)",
            data=fake_data,
        )

        with patch(
            "app.api.v1.admin_status.ProviderCanaryJob", return_value=fake_job
        ):
            r = client.post("/api/v1/admin/status/canary", headers=_auth(admin["token"]))

        assert r.status_code == 200, r.text
        data = r.json()
        canary = data["canary"]
        assert canary["success"] is True
        assert canary["message"] == "Canary OK (AS24 listings>0, mobile=ok)"
        assert canary["finished_at"] is not None
        assert canary["autoscout24"] == {
            "count": 7,
            "sample_id": "as24-1",
            "sample_price": 2500,
        }
        assert canary["mobile_de"] == {"count": 4}
        assert canary["strict_mobile"] is True
        assert canary["mobile_status"] == "ok"

    def test_admin_business_failure_is_200(self, client: TestClient) -> None:
        admin = _register(client, role=Role.ADMIN)

        fake_data = {
            "autoscout24": {"count": 0},
            "mobile_de": {"count": 0},
            "strict_mobile": False,
            "mobile_status": "empty",
        }
        fake_job = _FakeCanaryJob(
            success=False,
            message="Canary FAIL: AutoScout24 devolvió 0 listings o error",
            data=fake_data,
        )

        with patch(
            "app.api.v1.admin_status.ProviderCanaryJob", return_value=fake_job
        ):
            r = client.post("/api/v1/admin/status/canary", headers=_auth(admin["token"]))

        # El FAIL de negocio NO debe ser HTTP 500.
        assert r.status_code == 200, r.text
        canary = r.json()["canary"]
        assert canary["success"] is False
        assert "FAIL" in canary["message"]
        assert canary["mobile_status"] == "empty"
        assert canary["strict_mobile"] is False

    def test_get_status_reflects_posted_snapshot(self, client: TestClient) -> None:
        admin = _register(client, role=Role.ADMIN)

        fake_data = {
            "autoscout24": {"count": 3},
            "mobile_de": {"count": 2},
            "strict_mobile": False,
            "mobile_status": "ok",
        }
        fake_job = _FakeCanaryJob(
            success=True,
            message="Canary OK (AS24 listings>0, mobile=ok)",
            data=fake_data,
        )

        with patch(
            "app.api.v1.admin_status.ProviderCanaryJob", return_value=fake_job
        ):
            post = client.post(
                "/api/v1/admin/status/canary", headers=_auth(admin["token"])
            )
        assert post.status_code == 200, post.text
        post_canary = post.json()["canary"]

        # GET posterior debe ver el mismo snapshot compartido (canary_state).
        r = client.get("/api/v1/admin/status", headers=_auth(admin["token"]))
        assert r.status_code == 200, r.text
        get_canary = r.json()["canary"]
        assert get_canary["success"] == post_canary["success"]
        assert get_canary["message"] == post_canary["message"]
        assert get_canary["finished_at"] == post_canary["finished_at"]
        assert get_canary["autoscout24"] == post_canary["autoscout24"]
        assert get_canary["mobile_de"] == post_canary["mobile_de"]
        assert get_canary["strict_mobile"] == post_canary["strict_mobile"]
        assert get_canary["mobile_status"] == post_canary["mobile_status"]

    def test_admin_mock_job_call_used(self, client: TestClient) -> None:
        """Asegura que el endpoint instancia y ejecuta el job mockeado."""
        admin = _register(client, role=Role.ADMIN)

        fake_job = _FakeCanaryJob(
            success=True,
            message="mock executed",
            data={"autoscout24": {"count": 1}, "mobile_de": {}, "mobile_status": "ok"},
        )

        with patch(
            "app.api.v1.admin_status.ProviderCanaryJob", return_value=fake_job
        ) as patched_job:
            r = client.post(
                "/api/v1/admin/status/canary", headers=_auth(admin["token"])
            )

        assert r.status_code == 200, r.text
        # El endpoint crea una instancia del fake (patch) y ejecuta su método execute.
        assert patched_job.called
        assert r.json()["canary"]["message"] == "mock executed"
