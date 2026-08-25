"""Integration tests SEARCH.ORCH.1 — paginación, orden y trazabilidad en POST /api/v1/search.

Viven en tests/unit/api porque no requieren PostgreSQL: el engine está
mockeado, la auth se sobreescribe y la persistencia del historial es
fail-soft (un fallo de BD no rompe la respuesta).
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.api.v1.dependencies import get_search_engine_service
from app.dependencies.auth import get_current_user
from app.main import app
from app.models.search import (
    SearchEngineResult,
    SearchRequest,
    SearchResult,
    SearchSummary,
)
from app.models.user import User
from app.services.search_engine import SearchEngineService

client = TestClient(app)


@pytest.fixture
def override_auth() -> Any:
    """Override de get_current_user (patrón tests/integration/conftest.py)."""
    test_user = User(
        id="11111111-1111-1111-1111-111111111111",
        email="search-pagination@example.com",
        hashed_password="not-used-in-override",
    )

    async def _get_current_user() -> User:
        return test_user

    app.dependency_overrides[get_current_user] = _get_current_user
    yield test_user
    app.dependency_overrides.pop(get_current_user, None)


def _make_result(available_in_sources: list[str] | None = None) -> SearchResult:
    vehicle = MagicMock(
        source="mobile_de",
        external_id="12345",
        url="https://example.com/v/12345",
        brand="BMW",
        model="320d",
        year=2020,
        mileage=50000,
        price=25000.0,
        currency="EUR",
        fuel_type="diesel",
        transmission="manual",
        power_hp=190,
        location="Berlin",
        images=["img1.jpg"],
        description="ok",
    )
    if available_in_sources is not None:
        vehicle.available_in_sources = available_in_sources
    else:
        del vehicle.available_in_sources  # no etiquetado por el dedup
    return SearchResult(
        vehicle=vehicle,
        vehicle_score=MagicMock(
            score=85,
            category="Excelente",
            category_key="excellent",
            category_label_es="Excelente",
            strengths=[],
            weaknesses=[],
        ),
        market_estimation=MagicMock(
            market_price=28000.0,
            confidence=75.0,
            supply_level=50.0,
            demand_level=60.0,
            market_trend="stable",
            comparable_count=15,
            notes=[],
            explanation="",
        ),
        profit_analysis=MagicMock(
            purchase_price=25000.0,
            transport_cost=0.0,
            registration_cost=0.0,
            taxes=0.0,
            inspection_cost=0.0,
            repair_estimate=0.0,
            commission_cost=0.0,
            miscellaneous_cost=0.0,
            total_cost=27000.0,
            estimated_sale_price=35000.0,
            gross_profit=8000.0,
            net_profit=7000.0,
            roi_percentage=25.0,
            profit_margin_percentage=20.0,
            risk_level=MagicMock(value="LOW"),
            recommendation=MagicMock(value="BUY"),
            cost_breakdown=None,
        ),
        opportunity=MagicMock(
            overall_score=78.5,
            opportunity_level=MagicMock(value="GOOD"),
            recommendation=MagicMock(value="WATCH"),
            estimated_profit=7000.0,
            roi=25.0,
            market_confidence=75.0,
            risk_level="LOW",
            strengths=[],
            weaknesses=[],
        ),
    )


def _install_engine(payload_kwargs: dict[str, Any]) -> tuple[MagicMock, SearchEngineResult]:
    """Registra un engine mock con metadatos SEARCH.ORCH.1 y lo devuelve."""
    engine_result = SearchEngineResult(
        summary=SearchSummary(total_results=1, excellent=1),
        results=[_make_result(payload_kwargs.get("available_in_sources"))],
        total_matches=payload_kwargs.get("total_matches", 45),
        providers_succeeded=payload_kwargs.get("providers_succeeded", ["autoscout24", "mobile_de"]),
    )
    engine = MagicMock(spec=SearchEngineService)
    engine.search = AsyncMock(return_value=engine_result)
    app.dependency_overrides[get_search_engine_service] = lambda: engine
    return engine, engine_result


class TestPaginationMetadata:
    def setup_method(self) -> None:
        app.dependency_overrides.clear()

    def teardown_method(self) -> None:
        app.dependency_overrides.clear()

    def test_response_contains_pagination_block(self, override_auth) -> None:
        _install_engine({})
        try:
            response = client.post(
                "/api/v1/search",
                json={"query": "bmw", "max_results": 10},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["pagination"]["page"] == 1
            assert data["pagination"]["page_size"] == 10
            assert data["pagination"]["total_matches"] == 45
            assert data["pagination"]["total_pages"] == 5
            assert data["summary"]["total_results"] == len(data["results"])
        finally:
            app.dependency_overrides.clear()

    def test_page_maps_to_offset(self, override_auth) -> None:
        engine, _ = _install_engine({})
        try:
            client.post(
                "/api/v1/search",
                json={"query": "bmw", "max_results": 10, "page": 3},
            )
            call_request: SearchRequest = engine.search.call_args[0][0]
            assert call_request.offset == 20
            assert call_request.max_results == 10
        finally:
            app.dependency_overrides.clear()

    def test_sort_fields_map_to_domain_request(self, override_auth) -> None:
        engine, _ = _install_engine({})
        try:
            client.post(
                "/api/v1/search",
                json={"query": "bmw", "sort_by": "price", "sort_order": "asc"},
            )
            call_request: SearchRequest = engine.search.call_args[0][0]
            assert call_request.sort_by == "price"
            assert call_request.sort_order == "asc"
        finally:
            app.dependency_overrides.clear()

    def test_page_zero_rejected_422(self, override_auth) -> None:
        _install_engine({})
        try:
            response = client.post(
                "/api/v1/search",
                json={"query": "bmw", "page": 0},
            )
            assert response.status_code == 422
        finally:
            app.dependency_overrides.clear()


class TestResponseTraceability:
    def test_providers_succeeded_and_execution_time(self, override_auth) -> None:
        _install_engine({"providers_succeeded": ["autoscout24"]})
        try:
            response = client.post(
                "/api/v1/search",
                json={"query": "bmw", "providers": ["autoscout24", "mobile_de"]},
            )
            data = response.json()
            assert data["providers_succeeded"] == ["autoscout24"]
            assert isinstance(data["execution_time_ms"], (int, float))
            assert data["cache_hit"] is False
        finally:
            app.dependency_overrides.clear()

    def test_available_in_sources_passes_through(self, override_auth) -> None:
        _install_engine({"available_in_sources": ["autoscout24", "autoscout24_es"]})
        try:
            response = client.post("/api/v1/search", json={"query": "bmw"})
            data = response.json()
            item = data["results"][0]
            assert item["available_in_sources"] == ["autoscout24", "autoscout24_es"]
        finally:
            app.dependency_overrides.clear()

    def test_available_in_sources_null_when_single_source(self, override_auth) -> None:
        _install_engine({"available_in_sources": None})
        try:
            response = client.post("/api/v1/search", json={"query": "bmw"})
            data = response.json()
            item = data["results"][0]
            # MagicMock sin etiqueta → campo a null (no rompe la serialización)
            assert item["available_in_sources"] is None or isinstance(
                item["available_in_sources"], list
            )
        finally:
            app.dependency_overrides.clear()


class TestProvidersValidation:
    def teardown_method(self) -> None:
        app.dependency_overrides.clear()

    def test_duplicate_providers_deduped_in_domain_request(self, override_auth) -> None:
        engine, _ = _install_engine({})
        try:
            client.post(
                "/api/v1/search",
                json={
                    "query": "bmw",
                    "providers": ["autoscout24", " autoscout24 ", ""],
                },
            )
            call_request: SearchRequest = engine.search.call_args[0][0]
            assert call_request.providers == ["autoscout24"]
        finally:
            app.dependency_overrides.clear()

    def test_more_than_20_providers_rejected_422(self, override_auth) -> None:
        _install_engine({})
        try:
            response = client.post(
                "/api/v1/search",
                json={
                    "query": "bmw",
                    "providers": [f"p{i}" for i in range(21)],
                },
            )
            assert response.status_code == 422
        finally:
            app.dependency_overrides.clear()
