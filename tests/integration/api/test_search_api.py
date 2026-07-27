"""Integration tests for the search endpoint.

POST /api/v1/search
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient

from app.api.v1.dependencies import get_search_engine_service
from app.main import app
from app.models.search import (
    SearchEngineResult,
    SearchRequest,
    SearchResult,
    SearchSummary,
)
from app.services.search_engine import SearchEngineService

client = TestClient(app)


def _make_mock_search_result() -> SearchResult:
    """Creates a simulated SearchResult with all analysis data."""
    vehicle = MagicMock(
        source="mobile_de",
        external_id="12345",
        url="https://example.com/vehicle/12345",
        brand="BMW",
        model="320d",
        year=2020,
        mileage=50000,
        fuel_type="diesel",
        transmission="manual",
        power_hp=190,
        price=25000.0,
        currency="EUR",
        location="Berlin",
        images=["img1.jpg"],
        description="Good condition",
    )

    vehicle_score = MagicMock(
        score=85,
        category="Excelente",
        strengths=["Buen precio", "Bajo km"],
        weaknesses=[],
    )

    market_estimation = MagicMock(
        market_price=28000.0,
        confidence=75.0,
        supply_level=50.0,
        demand_level=60.0,
        market_trend="stable",
        comparable_count=15,
        notes=[],
    )

    cost_breakdown = MagicMock(
        purchase_price=25000.0,
        transport_cost=500.0,
        registration_cost=300.0,
        taxes=1500.0,
        inspection_cost=100.0,
        repair_estimate=200.0,
        commission_cost=250.0,
        miscellaneous_cost=150.0,
        total_fixed_costs=1050.0,
        total_variable_costs=1950.0,
        total_cost=28000.0,
    )

    profit_analysis = MagicMock(
        purchase_price=25000.0,
        transport_cost=500.0,
        registration_cost=300.0,
        taxes=1500.0,
        inspection_cost=100.0,
        repair_estimate=200.0,
        commission_cost=250.0,
        miscellaneous_cost=150.0,
        total_cost=28000.0,
        estimated_sale_price=35000.0,
        gross_profit=10000.0,
        net_profit=7000.0,
        roi_percentage=25.0,
        profit_margin_percentage=20.0,
        risk_level=MagicMock(value="LOW"),
        recommendation=MagicMock(value="BUY"),
        cost_breakdown=cost_breakdown,
    )

    opportunity = MagicMock(
        overall_score=78.5,
        opportunity_level=MagicMock(value="GOOD"),
        recommendation=MagicMock(value="WATCH"),
        estimated_profit=7000.0,
        roi=25.0,
        market_confidence=75.0,
        risk_level="LOW",
        strengths=["Buena oportunidad"],
        weaknesses=["Mercado incierto"],
    )

    return SearchResult(
        vehicle=vehicle,
        vehicle_score=vehicle_score,
        market_estimation=market_estimation,
        profit_analysis=profit_analysis,
        opportunity=opportunity,
    )


def _make_mock_engine_full() -> MagicMock:
    """Creates a SearchEngineService mock with real results."""
    engine = MagicMock(spec=SearchEngineService)
    result = SearchEngineResult(
        summary=SearchSummary(
            total_results=1,
            excellent=1,
            good=0,
            average=0,
            poor=0,
            rejected=0,
        ),
        results=[_make_mock_search_result()],
    )
    engine.search = AsyncMock(return_value=result)
    return engine


def _make_mock_engine_empty() -> MagicMock:
    """Creates a SearchEngineService mock with empty results."""
    engine = MagicMock(spec=SearchEngineService)
    result = SearchEngineResult(
        summary=SearchSummary(
            total_results=0,
            excellent=0,
            good=0,
            average=0,
            poor=0,
            rejected=0,
        ),
        results=[],
    )
    engine.search = AsyncMock(return_value=result)
    return engine


class TestSearchEndpoint:

    def test_search_returns_200(self) -> None:
        """POST /api/v1/search should return 200 OK."""
        mock_engine = _make_mock_engine_full()
        app.dependency_overrides[get_search_engine_service] = lambda: mock_engine
        try:
            response = client.post(
                "/api/v1/search",
                json={
                    "query": "BMW 320d",
                    "providers": ["mobile_de", "autoscout24"],
                    "max_results": 30,
                    "min_price": 15000,
                    "max_price": 35000,
                },
            )
            assert response.status_code == 200
        finally:
            app.dependency_overrides.clear()

    def test_search_returns_json(self) -> None:
        """Response must be JSON."""
        mock_engine = _make_mock_engine_full()
        app.dependency_overrides[get_search_engine_service] = lambda: mock_engine
        try:
            response = client.post(
                "/api/v1/search",
                json={
                    "query": "BMW 320d",
                    "providers": ["mobile_de", "autoscout24"],
                },
            )
            assert response.headers["content-type"] == "application/json"
        finally:
            app.dependency_overrides.clear()

    def test_search_has_summary(self) -> None:
        """Response must contain a summary."""
        mock_engine = _make_mock_engine_full()
        app.dependency_overrides[get_search_engine_service] = lambda: mock_engine
        try:
            response = client.post(
                "/api/v1/search",
                json={"query": "BMW 320d"},
            )
            data = response.json()
            assert "summary" in data
            assert "total_results" in data["summary"]
            assert data["summary"]["total_results"] > 0
        finally:
            app.dependency_overrides.clear()

    def test_search_has_results(self) -> None:
        """Response must contain results list."""
        mock_engine = _make_mock_engine_full()
        app.dependency_overrides[get_search_engine_service] = lambda: mock_engine
        try:
            response = client.post(
                "/api/v1/search",
                json={"query": "BMW 320d"},
            )
            data = response.json()
            assert "results" in data
            assert isinstance(data["results"], list)
            assert len(data["results"]) > 0
        finally:
            app.dependency_overrides.clear()

    def test_search_result_has_vehicle_info(self) -> None:
        """Each result must have basic vehicle info."""
        mock_engine = _make_mock_engine_full()
        app.dependency_overrides[get_search_engine_service] = lambda: mock_engine
        try:
            response = client.post(
                "/api/v1/search",
                json={"query": "BMW 320d"},
            )
            data = response.json()
            item = data["results"][0]
            assert "source" in item
            assert "external_id" in item
            assert "brand" in item
            assert "model" in item
            assert "price" in item
        finally:
            app.dependency_overrides.clear()

    def test_search_result_has_analysis(self) -> None:
        """Each result must have complete analysis."""
        mock_engine = _make_mock_engine_full()
        app.dependency_overrides[get_search_engine_service] = lambda: mock_engine
        try:
            response = client.post(
                "/api/v1/search",
                json={"query": "BMW 320d"},
            )
            data = response.json()
            item = data["results"][0]
            assert "vehicle_score" in item
            assert "market_estimation" in item
            assert "profit_analysis" in item
            assert "opportunity" in item
        finally:
            app.dependency_overrides.clear()

    def test_empty_search(self) -> None:
        """Search with no results should return empty list."""
        mock_engine = _make_mock_engine_empty()
        app.dependency_overrides[get_search_engine_service] = lambda: mock_engine
        try:
            response = client.post(
                "/api/v1/search",
                json={"query": "ZZZZZ"},
            )
            data = response.json()
            assert data["summary"]["total_results"] == 0
            assert data["results"] == []
        finally:
            app.dependency_overrides.clear()

    def test_min_price_max_price_mapping(self) -> None:
        """min_price and max_price must map to budget_min/budget_max."""
        mock_engine = MagicMock(spec=SearchEngineService)
        mock_engine.search = AsyncMock()
        app.dependency_overrides[get_search_engine_service] = lambda: mock_engine
        try:
            client.post(
                "/api/v1/search",
                json={
                    "query": "BMW",
                    "min_price": 10000,
                    "max_price": 30000,
                },
            )
            call_request: SearchRequest = mock_engine.search.call_args[0][0]
            assert call_request.budget_min == 10000
            assert call_request.budget_max == 30000
        finally:
            app.dependency_overrides.clear()

    def test_min_price_greater_than_max_returns_422(self) -> None:
        """If min_price > max_price, must return 422."""
        mock_engine = _make_mock_engine_full()
        app.dependency_overrides[get_search_engine_service] = lambda: mock_engine
        try:
            response = client.post(
                "/api/v1/search",
                json={
                    "query": "BMW",
                    "min_price": 50000,
                    "max_price": 10000,
                },
            )
            assert response.status_code == 422
        finally:
            app.dependency_overrides.clear()

    def test_missing_query_returns_422(self) -> None:
        """If query is missing, must return 422."""
        mock_engine = _make_mock_engine_full()
        app.dependency_overrides[get_search_engine_service] = lambda: mock_engine
        try:
            response = client.post(
                "/api/v1/search",
                json={},
            )
            assert response.status_code == 422
        finally:
            app.dependency_overrides.clear()

    def test_search_serializes_to_json(self) -> None:
        """Response must be JSON serializable."""
        mock_engine = _make_mock_engine_full()
        app.dependency_overrides[get_search_engine_service] = lambda: mock_engine
        try:
            response = client.post(
                "/api/v1/search",
                json={"query": "BMW 320d"},
            )

            # Must not raise exception
            data = json.loads(response.text)
            assert data["summary"]["total_results"] > 0
            assert len(data["results"]) > 0
        finally:
            app.dependency_overrides.clear()