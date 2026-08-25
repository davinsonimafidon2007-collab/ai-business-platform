"""Tests del registry de agents y del API /api/v1/agents (AUDIT.AGENTS.1)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.agents.registry import build_registry, describe_agents
from app.api.v1.dependencies import get_pipeline_orchestrator
from app.dependencies.auth import get_current_user
from app.main import app
from app.models.search import SearchEngineResult, SearchResult, SearchSummary
from app.models.user import User
from app.orchestrator.pipeline import PipelineOrchestrator


# =============================================================================
# Registry
# =============================================================================


def test_registry_contains_all_six_real_agents():
    registry = build_registry()

    assert set(registry) == {
        "search",
        "scoring",
        "opportunity",
        "negotiation",
        "alert",
        "budget_search",
    }
    for instance in registry.values():
        assert instance.description  # metadatos reales, no vacíos


def test_describe_agents_reports_active_status_and_timeouts():
    entries = describe_agents()
    by_id = {e["id"]: e for e in entries}

    assert len(entries) == 6
    assert all(e["status"] == "active" for e in entries)
    assert by_id["search"]["timeout_seconds"] == 120.0
    assert by_id["scoring"]["timeout_seconds"] == 10.0
    assert by_id["negotiation"]["role"] == "negotiation"


# =============================================================================
# Endpoints /api/v1/agents
# =============================================================================

client = TestClient(app)


def _override_user():
    async def _get_current_user() -> User:
        return User(id="user-1", email="test@example.com", hashed_password="x")

    return _get_current_user


@pytest.fixture(autouse=True)
def _auth_override():
    app.dependency_overrides[get_current_user] = _override_user()
    yield
    app.dependency_overrides.clear()


def test_list_agents_returns_real_registry():
    response = client.get("/api/v1/agents")

    assert response.status_code == 200
    payload = response.json()
    ids = [a["id"] for a in payload]
    assert set(ids) == {
        "search",
        "scoring",
        "opportunity",
        "negotiation",
        "alert",
        "budget_search",
    }
    scoring = next(a for a in payload if a["id"] == "scoring")
    assert scoring["status"] == "active"
    assert scoring["metrics_available"] is False


def test_get_agent_returns_detail_for_known_id():
    response = client.get("/api/v1/agents/negotiation")

    assert response.status_code == 200
    assert response.json()["name"] == "negotiation_agent"


def test_get_agent_returns_404_for_unknown_id():
    response = client.get("/api/v1/agents/no_existe")

    assert response.status_code == 404


# =============================================================================
# POST /api/v1/agents/pipeline/run — pipeline SEARCH → ALERT con agents reales
# =============================================================================


class _Vehicle:
    external_id = "ext-123"


class _Opportunity:
    opportunity_level = "EXCELLENT"
    recommendation = "BUY_NOW"
    estimated_profit = 3000.0
    roi = 20.0


def _fake_search_result() -> SearchResult:
    return SearchResult(
        # DTOs reales (dataclasses): el endpoint serializa objetos de dominio.
        vehicle=VehicleSearchResult(source="mobile_de", external_id="ext-123"),
        vehicle_score={"score": 90},
        market_estimation={"confidence": 80},
        profit_analysis={"net_profit": 3000.0},
        opportunity=OpportunityAnalysis(
            overall_score=85.0,
            opportunity_level=OpportunityLevel.EXCELLENT,
            recommendation=Recommendation.BUY_NOW,
            estimated_profit=3000.0,
            roi=20.0,
            market_confidence=80.0,
            risk_level="LOW",
        ),
    )


class _FakeEngine:
    async def search(self, request):
        return SearchEngineResult(
            summary=SearchSummary(total_results=1, excellent=1),
            results=[_fake_search_result()],
            provider_issues=[],
        )


@pytest.fixture
def pipeline_client():
    orchestrator = PipelineOrchestrator(search_engine=_FakeEngine())
    app.dependency_overrides[get_pipeline_orchestrator] = lambda: orchestrator
    yield client
    app.dependency_overrides.pop(get_pipeline_orchestrator, None)


def test_pipeline_run_returns_results_and_alerts(pipeline_client):
    response = pipeline_client.post(
        "/api/v1/agents/pipeline/run",
        json={"query": "golf", "max_results": 10, "alert_rules": {"min_level": "GOOD"}},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_results"] == 1
    assert payload["alerts"], "la regla min_level GOOD debe disparar con EXCELLENT"
    alert = payload["alerts"][0]
    assert alert["external_id"] == "ext-123"
    assert any("EXCELLENT" in a for a in alert["alerts"])


def test_pipeline_run_without_rules_has_no_alerts(pipeline_client):
    response = pipeline_client.post(
        "/api/v1/agents/pipeline/run",
        json={"query": "golf"},
    )

    assert response.status_code == 200
    assert response.json()["alerts"] == []


def test_pipeline_run_validates_input(pipeline_client):
    response = pipeline_client.post(
        "/api/v1/agents/pipeline/run",
        json={"query": ""},
    )

    assert response.status_code == 422
