"""Tests del endpoint POST /vehicles/{id}/simulate-profit (Task B.2)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.api.v1 import vehicles as vehicles_module
from app.api.v1.dependencies import get_profit_analyzer
from app.dependencies.auth import get_current_user
from app.main import app
from app.models.user import User
from app.models.vehicle import Vehicle
from app.services.profit_analyzer import ProfitAnalysis, ProfitAnalyzer, Recommendation, RiskLevel

client = TestClient(app)


def _make_analysis() -> ProfitAnalysis:
    return ProfitAnalysis(
        purchase_price=18000.0,
        transport_cost=1200.0,
        registration_cost=450.0,
        taxes=1800.0,
        inspection_cost=90.0,
        repair_estimate=540.0,
        commission_cost=720.0,
        miscellaneous_cost=480.0,
        total_cost=23280.0,
        estimated_sale_price=24000.0,
        gross_profit=6000.0,
        net_profit=720.0,
        roi_percentage=3.09,
        profit_margin_percentage=3.0,
        risk_level=RiskLevel.MEDIUM,
        recommendation=Recommendation.CONSIDER,
        cost_breakdown=MagicMock(
            transport_cost=1200.0,
            registration_cost=450.0,
            taxes=1800.0,
            inspection_cost=90.0,
            commission_cost=720.0,
            repair_estimate=540.0,
            miscellaneous_cost=480.0,
        ),
    )


@pytest.fixture
def override_deps() -> None:
    current_user = User(id="user-1", email="test@example.com", hashed_password="x")

    async def _get_current_user() -> User:
        return current_user

    async def _get_vehicle_service() -> AsyncMock:
        svc = AsyncMock()
        vehicle = Vehicle(
            id="vehicle-1",
            user_id="user-1",
            source="mobile_de",
            external_id="123",
            brand="BMW",
            model="320d",
            price=18000.0,
        )
        svc.get_vehicle = AsyncMock(return_value=vehicle)
        return svc

    def _get_profit_analyzer() -> ProfitAnalyzer:
        analyzer = MagicMock(spec=ProfitAnalyzer)
        analyzer.analyze = MagicMock(return_value=_make_analysis())
        return analyzer

    app.dependency_overrides[get_current_user] = _get_current_user
    app.dependency_overrides[vehicles_module.get_vehicle_service] = _get_vehicle_service
    app.dependency_overrides[get_profit_analyzer] = _get_profit_analyzer
    yield
    app.dependency_overrides.clear()


def test_simulate_profit_returns_200(override_deps: None) -> None:
    response = client.post(
        "/api/v1/vehicles/vehicle-1/simulate-profit",
        json={"profile_name": "ES", "purchase_price": 18000, "estimated_sale_price": 24000},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["profile_name"] == "ES"
    assert data["purchase_price"] == 18000.0
    assert data["estimated_sale_price"] == 24000.0
    assert data["total_cost"] == 23280.0
    assert data["net_profit"] == 720.0
    assert data["roi_percentage"] == 3.09
    assert data["recommendation"] == "CONSIDER"
    assert data["risk_level"] == "MEDIUM"
    assert data["transport_cost"] == 1200.0
    assert data["registration_cost"] == 450.0
    assert data["taxes"] == 1800.0
    assert data["inspection_cost"] == 90.0
    assert data["commission_cost"] == 720.0
    assert data["repair_estimate"] == 540.0
    assert data["miscellaneous_cost"] == 480.0


def test_simulate_profit_es_equals_spain(override_deps: None) -> None:
    """ES y SPAIN deben producir el mismo resultado (mismo perfil)."""
    from app.config.import_costs import get_profile

    es = get_profile("ES")
    spain = get_profile("SPAIN")
    assert es.transport_cost == spain.transport_cost
    assert es.registration_cost == spain.registration_cost