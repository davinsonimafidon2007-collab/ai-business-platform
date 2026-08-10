"""Integration tests for the search endpoint.

POST /api/v1/search
"""

from __future__ import annotations

import json
from typing import Any
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
        category_key="excellent",
        category_label_es="Excelente",
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
        explanation="",
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

    def test_search_returns_200(self, override_auth) -> None:
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

    def test_search_returns_json(self, override_auth) -> None:
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

    def test_search_has_summary(self, override_auth) -> None:
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

    def test_search_has_results(self, override_auth) -> None:
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

    def test_search_result_has_vehicle_info(self, override_auth) -> None:
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

    def test_search_result_has_analysis(self, override_auth) -> None:
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

    def test_empty_search(self, override_auth) -> None:
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

    def test_min_price_max_price_mapping(self, override_auth) -> None:
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

    def test_min_price_greater_than_max_returns_422(self, override_auth) -> None:
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

    def test_missing_query_returns_422(self, override_auth) -> None:
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

    def test_search_serializes_to_json(self, override_auth) -> None:
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


# =============================================================================
# ES-specific API integration tests
# =============================================================================


def _make_es_result_item() -> dict[str, Any]:
    """Mock result from autoscout24_es provider for API tests."""
    return {
        "source": "autoscout24_es",
        "external_id": "ES-8801",
        "url": "https://www.autoscout24.es/lst/bmw/320?xyz=8801",
        "brand": "BMW",
        "model": "320d",
        "year": 2021,
        "mileage": 45000,
        "fuel_type": "diesel",
        "transmission": "automatic",
        "power_hp": 190,
        "price": 28000.0,
        "currency": "EUR",
        "location": "Madrid",
        "images": ["https://img.autoscout24.es/es8801_1.jpg"],
        "description": "BMW 320d en buen estado",
        "vehicle_score": {
            "score": 80,
            "category": "Muy bueno",
            "category_key": "good",
            "category_label_es": "Muy bueno",
            "strengths": ["Precio competitivo"],
            "weaknesses": ["Kilometraje elevado"],
        },
        "market_estimation": {
            "market_price": 30000.0,
            "confidence": 75.0,
            "supply_level": 55.0,
            "demand_level": 65.0,
            "market_trend": "stable",
            "comparable_count": 12,
            "notes": [],
            "explanation": "",
            "provider_sources": ["autoscout24_es"],
        },
        "profit_analysis": {
            "purchase_price": 28000.0,
            "transport_cost": 300.0,
            "registration_cost": 200.0,
            "taxes": 3500.0,
            "inspection_cost": 100.0,
            "repair_estimate": 500.0,
            "commission_cost": 0.0,
            "miscellaneous_cost": 150.0,
            "total_cost": 32650.0,
            "estimated_sale_price": 36000.0,
            "gross_profit": 3350.0,
            "net_profit": 690.0,
            "roi_percentage": 2.4,
            "profit_margin_percentage": 2.3,
            "risk_level": "LOW",
            "recommendation": "BUY",
            "cost_breakdown": None,
        },
        "opportunity": {
            "overall_score": 72.5,
            "opportunity_level": "GOOD",
            "recommendation": "BUY",
            "estimated_profit": 690.0,
            "roi": 2.4,
            "market_confidence": 75.0,
            "risk_level": "LOW",
            "strengths": ["Precio bajo vs mercado"],
            "weaknesses": [],
            "reasons": ["Good ROI"],
        },
        "recommendation_label_es": "Comprar",
        "risk_label_es": "Bajo",
        "negotiation": None,
    }


def _make_mock_engine_es() -> MagicMock:
    """Mock engine with autoscout24_es source result."""
    engine = MagicMock(spec=SearchEngineService)
    from app.models.search import SearchResult, SearchSummary

    vehicle = MagicMock(
        source="autoscout24_es",
        external_id="ES-8801",
        url="https://www.autoscout24.es/lst/bmw/320?xyz=8801",
        brand="BMW",
        model="320d",
        year=2021,
        mileage=45000,
        fuel_type="diesel",
        transmission="automatic",
        power_hp=190,
        price=28000.0,
        currency="EUR",
        location="Madrid",
        images=["https://img.autoscout24.es/es8801_1.jpg"],
        description="BMW 320d en buen estado",
    )
    vehicle_score = MagicMock(
        score=80,
        category="Muy bueno",
        category_key="good",
        category_label_es="Muy bueno",
        strengths=["Precio competitivo"],
        weaknesses=["Kilometraje elevado"],
    )
    market_estimation = MagicMock(
        market_price=30000.0,
        confidence=75.0,
        supply_level=55.0,
        demand_level=65.0,
        market_trend="stable",
        comparable_count=12,
        notes=[],
        explanation="",
        provider_sources=["autoscout24_es"],
    )
    profit_analysis = MagicMock(
        purchase_price=28000.0,
        total_cost=32650.0,
        estimated_sale_price=36000.0,
        gross_profit=3350.0,
        net_profit=690.0,
        roi_percentage=2.4,
        profit_margin_percentage=2.3,
        risk_level=MagicMock(value="LOW"),
        recommendation=MagicMock(value="BUY"),
        cost_breakdown=None,
    )
    opportunity = MagicMock(
        overall_score=72.5,
        opportunity_level=MagicMock(value="GOOD"),
        recommendation=MagicMock(value="BUY"),
        estimated_profit=690.0,
        roi=2.4,
        market_confidence=75.0,
        risk_level="LOW",
        strengths=["Precio bajo vs mercado"],
        weaknesses=[],
        reasons=["Good ROI"],
    )
    result = SearchResult(
        vehicle=vehicle,
        vehicle_score=vehicle_score,
        market_estimation=market_estimation,
        profit_analysis=profit_analysis,
        opportunity=opportunity,
    )
    engine_result = SearchEngineResult(
        summary=SearchSummary(total_results=1, excellent=1, good=0, average=0, poor=0, rejected=0),
        results=[result],
    )
    engine.search = AsyncMock(return_value=engine_result)
    return engine


def _make_mock_engine_es_with_issues() -> MagicMock:
    """Mock engine that returns ES result but with provider issues (SEARCH.DIAG.1)."""
    from app.models.search import ProviderIssue

    engine = _make_mock_engine_es()
    engine_result = engine.search.return_value
    engine_result.provider_issues = [
        ProviderIssue(
            provider="mobile_de",
            stage="search",
            error_type="ProviderConnectionError",
            message="HTTP 403 anti-bot",
        ),
    ]
    engine.search = AsyncMock(return_value=engine_result)
    return engine


class TestSearchEndpointES:
    """Tests ES-specific behavior in the search API."""

    def test_es_provider_result_returns_200(self, override_auth) -> None:
        """POST /api/v1/search with autoscout24_es provider returns 200."""
        mock_engine = _make_mock_engine_es()
        app.dependency_overrides[get_search_engine_service] = lambda: mock_engine
        try:
            response = client.post(
                "/api/v1/search",
                json={
                    "query": "BMW 320d",
                    "providers": ["autoscout24_es"],
                    "max_results": 20,
                },
            )
            assert response.status_code == 200
        finally:
            app.dependency_overrides.clear()

    def test_es_result_has_source(self, override_auth) -> None:
        """Result vehicle has source='autoscout24_es'."""
        mock_engine = _make_mock_engine_es()
        app.dependency_overrides[get_search_engine_service] = lambda: mock_engine
        try:
            response = client.post(
                "/api/v1/search",
                json={"query": "BMW 320d", "providers": ["autoscout24_es"]},
            )
            data = response.json()
            item = data["results"][0]
            assert item["source"] == "autoscout24_es"
        finally:
            app.dependency_overrides.clear()

    def test_es_result_has_external_id(self, override_auth) -> None:
        """Result vehicle has external_id from autoscout24_es."""
        mock_engine = _make_mock_engine_es()
        app.dependency_overrides[get_search_engine_service] = lambda: mock_engine
        try:
            response = client.post(
                "/api/v1/search",
                json={"query": "BMW 320d", "providers": ["autoscout24_es"]},
            )
            data = response.json()
            item = data["results"][0]
            assert item["external_id"] == "ES-8801"
        finally:
            app.dependency_overrides.clear()

    def test_es_result_has_url(self, override_auth) -> None:
        """Result vehicle has URL pointing to autoscout24.es."""
        mock_engine = _make_mock_engine_es()
        app.dependency_overrides[get_search_engine_service] = lambda: mock_engine
        try:
            response = client.post(
                "/api/v1/search",
                json={"query": "BMW 320d", "providers": ["autoscout24_es"]},
            )
            data = response.json()
            item = data["results"][0]
            assert "autoscout24.es" in item["url"]
            assert item["url"].startswith("https://www.autoscout24.es/")
        finally:
            app.dependency_overrides.clear()

    def test_es_result_has_spanish_location(self, override_auth) -> None:
        """Result vehicle has Spanish location (Madrid)."""
        mock_engine = _make_mock_engine_es()
        app.dependency_overrides[get_search_engine_service] = lambda: mock_engine
        try:
            response = client.post(
                "/api/v1/search",
                json={"query": "BMW 320d", "providers": ["autoscout24_es"]},
            )
            data = response.json()
            item = data["results"][0]
            assert item["location"] == "Madrid"
        finally:
            app.dependency_overrides.clear()

    def test_es_result_has_es_labels(self, override_auth) -> None:
        """Result has ES-readable labels in nested schemas."""
        mock_engine = _make_mock_engine_es()
        app.dependency_overrides[get_search_engine_service] = lambda: mock_engine
        try:
            response = client.post(
                "/api/v1/search",
                json={"query": "BMW 320d", "providers": ["autoscout24_es"]},
            )
            data = response.json()
            item = data["results"][0]
            # ES labels are in the nested schemas
            assert item["profit_analysis"]["recommendation_label_es"] != ""
            assert item["profit_analysis"]["risk_label_es"] != ""
            assert item["opportunity"]["recommendation_label_es"] != ""
            assert item["opportunity"]["risk_label_es"] != ""
        finally:
            app.dependency_overrides.clear()

    def test_es_result_score_category_es(self, override_auth) -> None:
        """Vehicle score has ES category label."""
        mock_engine = _make_mock_engine_es()
        app.dependency_overrides[get_search_engine_service] = lambda: mock_engine
        try:
            response = client.post(
                "/api/v1/search",
                json={"query": "BMW 320d", "providers": ["autoscout24_es"]},
            )
            data = response.json()
            item = data["results"][0]
            vs = item["vehicle_score"]
            assert vs["category_label_es"] == "Muy bueno"
        finally:
            app.dependency_overrides.clear()

    def test_es_result_profit_analysis(self, override_auth) -> None:
        """Profit analysis has correct values from ES result."""
        mock_engine = _make_mock_engine_es()
        app.dependency_overrides[get_search_engine_service] = lambda: mock_engine
        try:
            response = client.post(
                "/api/v1/search",
                json={"query": "BMW 320d", "providers": ["autoscout24_es"]},
            )
            data = response.json()
            item = data["results"][0]
            pa = item["profit_analysis"]
            assert pa["purchase_price"] == 28000.0
            assert pa["net_profit"] == 690.0
            assert pa["recommendation"] == "BUY"
        finally:
            app.dependency_overrides.clear()

    def test_es_result_opportunity(self, override_auth) -> None:
        """Opportunity analysis has correct values from ES result."""
        mock_engine = _make_mock_engine_es()
        app.dependency_overrides[get_search_engine_service] = lambda: mock_engine
        try:
            response = client.post(
                "/api/v1/search",
                json={"query": "BMW 320d", "providers": ["autoscout24_es"]},
            )
            data = response.json()
            item = data["results"][0]
            opp = item["opportunity"]
            assert opp["overall_score"] == 72.5
            assert opp["opportunity_level"] == "GOOD"
        finally:
            app.dependency_overrides.clear()

    def test_es_result_has_images(self, override_auth) -> None:
        """Result vehicle has ES provider images."""
        mock_engine = _make_mock_engine_es()
        app.dependency_overrides[get_search_engine_service] = lambda: mock_engine
        try:
            response = client.post(
                "/api/v1/search",
                json={"query": "BMW 320d", "providers": ["autoscout24_es"]},
            )
            data = response.json()
            item = data["results"][0]
            assert len(item["images"]) >= 1
            assert all("autoscout24.es" in img or "autoscout24" in img for img in item["images"])
        finally:
            app.dependency_overrides.clear()

    def test_es_provider_failure_in_provider_issues(self, override_auth) -> None:
        """When a provider fails, provider_issues is populated (SEARCH.DIAG.1)."""
        mock_engine = _make_mock_engine_es_with_issues()
        app.dependency_overrides[get_search_engine_service] = lambda: mock_engine
        try:
            response = client.post(
                "/api/v1/search",
                json={"query": "BMW", "providers": ["autoscout24_es", "mobile_de"]},
            )
            data = response.json()
            assert len(data["provider_issues"]) >= 1
            assert data["provider_issues"][0]["provider"] == "mobile_de"
            assert data["provider_issues"][0]["stage"] == "search"
            assert "403" in data["provider_issues"][0]["message"]
        finally:
            app.dependency_overrides.clear()

    def test_es_results_empty(self, override_auth) -> None:
        """ES provider returns no results → empty results list."""
        mock_engine = _make_mock_engine_empty()
        app.dependency_overrides[get_search_engine_service] = lambda: mock_engine
        try:
            response = client.post(
                "/api/v1/search",
                json={"query": "Tesla Model X", "providers": ["autoscout24_es"]},
            )
            data = response.json()
            assert data["summary"]["total_results"] == 0
            assert data["results"] == []
        finally:
            app.dependency_overrides.clear()

    def test_es_and_de_providers_in_request(self, override_auth) -> None:
        """Request with both autoscout24 and autoscout24_es providers."""
        mock_engine = _make_mock_engine_es()
        app.dependency_overrides[get_search_engine_service] = lambda: mock_engine
        try:
            response = client.post(
                "/api/v1/search",
                json={
                    "query": "BMW 320d",
                    "providers": ["autoscout24", "autoscout24_es"],
                },
            )
            data = response.json()
            assert len(data["results"]) >= 1
        finally:
            app.dependency_overrides.clear()

    def test_es_result_json_serializable(self, override_auth) -> None:
        """ES result must be fully JSON serializable."""
        mock_engine = _make_mock_engine_es()
        app.dependency_overrides[get_search_engine_service] = lambda: mock_engine
        try:
            response = client.post(
                "/api/v1/search",
                json={"query": "BMW 320d", "providers": ["autoscout24_es"]},
            )
            assert response.status_code == 200
            # Must not raise
            json.loads(response.text)
        finally:
            app.dependency_overrides.clear()

    def test_es_result_with_budget_filter(self, override_auth) -> None:
        """Budget filter applies to ES results."""
        mock_engine = _make_mock_engine_es()
        app.dependency_overrides[get_search_engine_service] = lambda: mock_engine
        try:
            response = client.post(
                "/api/v1/search",
                json={
                    "query": "BMW 320d",
                    "providers": ["autoscout24_es"],
                    "min_price": 25000,
                    "max_price": 30000,
                },
            )
            data = response.json()
            item = data["results"][0]
            assert 25000 <= item["price"] <= 30000
        finally:
            app.dependency_overrides.clear()

    def test_es_market_estimation_provider_sources(self, override_auth) -> None:
        """Market estimation includes provider_sources from ES."""
        mock_engine = _make_mock_engine_es()
        app.dependency_overrides[get_search_engine_service] = lambda: mock_engine
        try:
            response = client.post(
                "/api/v1/search",
                json={"query": "BMW 320d", "providers": ["autoscout24_es"]},
            )
            data = response.json()
            me = data["results"][0]["market_estimation"]
            assert "autoscout24_es" in me["provider_sources"]
        finally:
            app.dependency_overrides.clear()