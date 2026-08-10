"""Tests del endpoint GET /api/v1/opportunities (Task C.1)."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.database import get_db_session
from app.dependencies.auth import get_current_user
from app.main import app
from app.models.opportunity import Opportunity
from app.models.user import User
from app.models.vehicle import Vehicle
from app.repositories.opportunity_repository import OpportunityRepository

client = TestClient(app)


def _make_opportunity(
    *,
    opp_id: str = "opp-1",
    vehicle_id: str = "vehicle-1",
    score: float = 85.5,
    profit: float = 3500.0,
    roi: float = 18.3,
    recommendation: str = "BUY_NOW",
    risk: str = "LOW",
) -> Opportunity:
    return Opportunity(
        id=opp_id,
        vehicle_id=vehicle_id,
        opportunity_score=score,
        profit=profit,
        roi=roi,
        recommendation=recommendation,
        risk=risk,
        created_at=datetime.now(UTC),
        analyzed_at=datetime.now(UTC),
    )


def _make_vehicle(*, vehicle_id: str = "vehicle-1") -> Vehicle:
    return Vehicle(
        id=vehicle_id,
        user_id="user-1",
        source="mobile_de",
        external_id="ext-1",
        brand="BMW",
        model="320d",
        year=2019,
        mileage=85000,
        price=18000.0,
        url="https://example.com/vehicle-1",
    )


@pytest.fixture
def auth_override() -> None:
    """Override get_current_user with a mock user."""
    current_user = User(id="user-1", email="test@example.com", hashed_password="x")

    async def _get_current_user() -> User:
        return current_user

    app.dependency_overrides[get_current_user] = _get_current_user
    yield
    app.dependency_overrides.clear()


def test_opportunities_requires_auth() -> None:
    """Sin token → 401."""
    response = client.get("/api/v1/opportunities")
    assert response.status_code == 401


def test_opportunities_returns_200_shape(auth_override: None) -> None:
    """Con auth + repo mock → 200 con shape items/total/limit/offset."""
    opp = _make_opportunity()
    vehicle = _make_vehicle()
    opp.vehicle = vehicle

    async def _fake_list_filtered(self, **kwargs):
        return [opp], 1

    async def _fake_execute(stmt):
        result = MagicMock()
        result.scalars.return_value.all.return_value = [vehicle]
        return result

    async def _get_db_session() -> AsyncMock:
        session = AsyncMock()
        session.execute = _fake_execute
        return session

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(OpportunityRepository, "list_filtered", _fake_list_filtered)
        app.dependency_overrides[get_db_session] = _get_db_session

        response = client.get("/api/v1/opportunities")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "limit" in data
        assert "offset" in data
        assert data["total"] == 1
        assert data["limit"] == 50
        assert data["offset"] == 0
        assert len(data["items"]) == 1
        item = data["items"][0]
        assert item["id"] == "opp-1"
        assert item["score"] == 85.5
        assert item["estimated_profit"] == 3500.0
        assert item["roi_percentage"] == 18.3
        assert item["recommendation"] == "BUY_NOW"
        assert item["risk_level"] == "LOW"
        assert item["recommendation_label_es"] == "Comprar ya"
        assert item["risk_label_es"] == "Bajo"
        assert item["vehicle"] is not None
        assert item["vehicle"]["brand"] == "BMW"
        assert item["vehicle"]["model"] == "320d"


def test_opportunities_passes_recommendation_filter(auth_override: None) -> None:
    """El filtro recommendation=BUY se pasa al repo."""
    captured: dict = {}

    async def _fake_list_filtered(self, **kwargs):
        captured.update(kwargs)
        return [], 0

    async def _fake_execute(stmt):
        result = MagicMock()
        result.scalars.return_value.all.return_value = []
        return result

    async def _get_db_session() -> AsyncMock:
        session = AsyncMock()
        session.execute = _fake_execute
        return session

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(OpportunityRepository, "list_filtered", _fake_list_filtered)
        app.dependency_overrides[get_db_session] = _get_db_session

        response = client.get("/api/v1/opportunities?recommendation=BUY")
        assert response.status_code == 200
        assert captured.get("recommendation") == "BUY"
        assert captured.get("user_id") == "user-1"