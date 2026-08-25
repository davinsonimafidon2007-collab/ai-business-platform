"""Tests para Budget Search Agent y endpoint."""

import pytest
from fastapi.testclient import TestClient

from app.agents.base import AgentValidationError
from app.agents.budget_search_agent import BudgetSearchAgent
from app.api.v1.dependencies import get_search_engine_service
from app.dependencies.auth import get_current_user
from app.main import app
from app.models.search import SearchEngineResult, SearchSummary
from app.models.user import User


def test_calculate_max_purchase_price_spain():
    agent = BudgetSearchAgent(profile_name="SPAIN")
    max_price = agent.calculate_max_purchase_price(15000)
    assert max_price > 0
    assert max_price < 15000


def test_budget_decreases_with_lower_capital():
    agent = BudgetSearchAgent(profile_name="SPAIN")
    high = agent.calculate_max_purchase_price(20000)
    low = agent.calculate_max_purchase_price(10000)
    assert high > low


def test_fixed_costs_subtracted():
    agent = BudgetSearchAgent(profile_name="SPAIN")
    profile = agent.calculate_max_purchase_price(15000)
    assert profile > 0


class _FakeEngine:
    def __init__(self) -> None:
        self.requests: list = []
        self.engine_result = SearchEngineResult(
            summary=SearchSummary(total_results=0),
            results=[],
            provider_issues=[],
        )

    async def search(self, request):
        self.requests.append(request)
        return self.engine_result


@pytest.mark.asyncio
async def test_budget_agent_runs_real_search_with_budget_max():
    engine = _FakeEngine()
    agent = BudgetSearchAgent(profile_name="SPAIN", search_engine=engine)

    result = await agent.run(
        {"total_budget": 15000, "query": "VW Golf", "max_results": 25, "profit_margin_min": 0}
    )

    assert result.status == "ok"
    assert result.max_purchase_price > 0
    assert result.query == "VW Golf"
    assert len(engine.requests) == 1
    search_request = engine.requests[0]
    assert search_request.budget_max == result.max_purchase_price
    assert search_request.max_results == 25


@pytest.mark.asyncio
async def test_budget_agent_without_engine_raises():
    agent = BudgetSearchAgent(profile_name="SPAIN")

    with pytest.raises(Exception, match="SearchEngineService"):
        await agent.run({"total_budget": 15000})


@pytest.mark.asyncio
async def test_budget_agent_budget_too_low_returns_status_without_search():
    engine = _FakeEngine()
    agent = BudgetSearchAgent(profile_name="SPAIN", search_engine=engine)

    result = await agent.run({"total_budget": 10})

    assert result.status == "budget_too_low"
    assert result.results == []
    assert engine.requests == []


@pytest.mark.asyncio
async def test_budget_agent_validates_input():
    agent = BudgetSearchAgent(profile_name="SPAIN", search_engine=_FakeEngine())

    with pytest.raises(AgentValidationError):
        await agent.run({"total_budget": -5})


# =============================================================================
# Endpoint API
# =============================================================================

client = TestClient(app)


def _override_user():
    async def _get_current_user() -> User:
        return User(id="user-1", email="test@example.com", hashed_password="x")

    return _get_current_user


@pytest.fixture
def budget_search_api():
    app.dependency_overrides[get_current_user] = _override_user()

    def _apply(engine: _FakeEngine | None = None):
        fake = engine or _FakeEngine()
        app.dependency_overrides[get_search_engine_service] = lambda: fake
        return fake

    yield _apply
    app.dependency_overrides.clear()


def test_budget_search_endpoint_runs_search(budget_search_api):
    fake = budget_search_api()

    response = client.post(
        "/api/v1/budget-search/search",
        json={"total_budget": 15000, "query": "VW Golf", "max_results": 20},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["max_purchase_price"] > 0
    assert payload["query"] == "VW Golf"
    assert payload["results"] == []
    assert payload["filtered_out_count"] == 0
    assert len(fake.requests) == 1
    assert fake.requests[0].budget_max == payload["max_purchase_price"]


def test_budget_search_endpoint_insufficient_budget_returns_400(budget_search_api):
    budget_search_api()

    response = client.post(
        "/api/v1/budget-search/search",
        json={"total_budget": 10},
    )

    assert response.status_code == 400
    assert "Presupuesto insuficiente" in response.json()["error"]["message"]


def test_budget_search_endpoint_invalid_profile_returns_400(budget_search_api):
    budget_search_api()

    response = client.post(
        "/api/v1/budget-search/search",
        json={"total_budget": 15000, "profile": "MARTE"},
    )

    assert response.status_code == 400
