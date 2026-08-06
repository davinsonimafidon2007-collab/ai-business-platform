"""Tests for PERF-001 server-side pagination caps.

The API rejects ``limit > 100`` with 422 (Query validation with ``le=100``),
and repositories clamp ``limit`` defensively via ``clamp_limit``.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.core.limits import MAX_LIST_LIMIT, clamp_limit
from app.database import get_db_session
from app.dependencies.auth import get_current_user
from app.main import app
from app.models.user import User

client = TestClient(app)


@pytest.fixture
def auth_override():
    current_user = User(id="user-1", email="test@example.com", hashed_password="x")

    async def _get_current_user() -> User:
        return current_user

    app.dependency_overrides[get_current_user] = _get_current_user
    yield
    app.dependency_overrides.clear()


async def _db() -> AsyncMock:
    return AsyncMock()


# ---------------------------------------------------------------------------
# clamp_limit (defensa en profundidad en repositorios)
# ---------------------------------------------------------------------------


def test_clamp_limit_caps_above_max() -> None:
    assert MAX_LIST_LIMIT == 100
    assert clamp_limit(1000) == 100
    assert clamp_limit(MAX_LIST_LIMIT) == 100


def test_clamp_limit_preserves_valid_and_floors() -> None:
    assert clamp_limit(50) == 50
    assert clamp_limit(1) == 1
    assert clamp_limit(0) == 1
    assert clamp_limit(-5) == 1


def test_clamp_limit_handles_bogus_input() -> None:
    assert clamp_limit("abc") == MAX_LIST_LIMIT
    assert clamp_limit(None) == MAX_LIST_LIMIT
    assert clamp_limit(3.9) == 3


# ---------------------------------------------------------------------------
# API validation: limit > 100 → 422
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "url",
    [
        "/api/v1/vehicles",
        "/api/v1/searches",
        "/api/v1/deals",
        "/api/v1/opportunities",
    ],
)
def test_listing_rejects_limit_above_max(url: str, auth_override) -> None:
    app.dependency_overrides[get_db_session] = _db
    response = client.get(f"{url}?limit=1000")
    assert response.status_code == 422


@pytest.mark.parametrize(
    "url,mock_repo",
    [
        (
            "/api/v1/vehicles",
            "app.repositories.vehicle_repository.VehicleRepository.list_by_user",
        ),
        (
            "/api/v1/searches",
            "app.repositories.search_repository.SearchRepository.list_by_user",
        ),
        (
            "/api/v1/deals",
            "app.repositories.deal_repository.DealRepository.list_for_user",
        ),
        (
            "/api/v1/opportunities",
            "app.repositories.opportunity_repository.OpportunityRepository.list_filtered",
        ),
    ],
)
def test_listing_accepts_limit_at_max(
    url: str, mock_repo: str, auth_override, monkeypatch
) -> None:
    app.dependency_overrides[get_db_session] = _db
    captured: dict = {}

    async def _fake_list(self, *args, **kwargs):
        captured.update(kwargs)
        # DealRepository / OpportunityRepository return (items, total);
        # Vehicle/Search repositories return a plain list.
        if self.__class__.__name__ in ("DealRepository", "OpportunityRepository"):
            return [], 0
        return []

    monkeypatch.setattr(mock_repo, _fake_list)
    response = client.get(f"{url}?limit=100")
    assert response.status_code == 200
    assert captured.get("limit") == 100
