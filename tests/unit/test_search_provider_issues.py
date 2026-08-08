"""SEARCH.DIAG.1: los fallos de provider dejan de ser silenciosos.

Antes, el orquestador capturaba cualquier excepción con `continue` y la
búsqueda devolvía 200 con `results: []`. Desde fuera era idéntico a "no hay
coches que encajen", y eso escondió un 404 real de AutoScout24 durante
E2E.MANUAL.PASS.1 (la URL se construía mal y nadie se enteró).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.search import SearchRequest
from app.providers.exceptions import (
    ProviderConnectionError,
    ProviderRateLimitError,
)
from app.services.provider_issue_labels import (
    build_provider_issue_payloads,
    provider_issue_message_es,
)
from app.services.search_orchestrator import SearchOrchestrator


def _orchestrator(registry: MagicMock, vehicle_service: MagicMock) -> SearchOrchestrator:
    return SearchOrchestrator(
        vehicle_service=vehicle_service,
        vehicle_scorer=MagicMock(),
        market_estimator=MagicMock(),
        profit_analyzer=MagicMock(),
        opportunity_finder=MagicMock(),
        provider_registry=registry,
    )


def _registry_with(provider: MagicMock) -> MagicMock:
    registry = MagicMock()
    registry.get.return_value = provider
    return registry


@pytest.mark.asyncio
async def test_provider_failure_is_reported_not_swallowed() -> None:
    """Un provider caído produce un issue, no un silencio."""
    vehicle_service = MagicMock()
    vehicle_service.search_from_provider = AsyncMock(
        side_effect=ProviderConnectionError("HTTP 403", provider="mobile_de")
    )
    orchestrator = _orchestrator(_registry_with(MagicMock()), vehicle_service)

    results = await orchestrator.search(
        SearchRequest(query="BMW", providers=["mobile_de"])
    )

    assert results == []
    issues = orchestrator.last_provider_issues
    assert len(issues) == 1
    assert issues[0].provider == "mobile_de"
    assert issues[0].stage == "search"
    assert issues[0].error_type == "ProviderConnectionError"


@pytest.mark.asyncio
async def test_unregistered_provider_is_reported() -> None:
    """Antes se hacía `continue` sin dejar rastro de que el provider no existe."""
    registry = MagicMock()
    registry.get.side_effect = KeyError("nope")
    orchestrator = _orchestrator(registry, MagicMock())

    await orchestrator.search(
        SearchRequest(query="BMW", providers=["provider_fantasma"])
    )

    issues = orchestrator.last_provider_issues
    assert len(issues) == 1
    assert issues[0].stage == "registry"
    assert issues[0].provider == "provider_fantasma"


@pytest.mark.asyncio
async def test_healthy_provider_with_no_matches_reports_no_issues() -> None:
    """Distinción clave: 0 resultados legítimos NO generan issues."""
    vehicle_service = MagicMock()
    vehicle_service.search_from_provider = AsyncMock(return_value=[])
    orchestrator = _orchestrator(_registry_with(MagicMock()), vehicle_service)

    results = await orchestrator.search(
        SearchRequest(query="BMW", providers=["autoscout24"])
    )

    assert results == []
    assert orchestrator.last_provider_issues == []


@pytest.mark.asyncio
async def test_one_provider_down_does_not_abort_the_others() -> None:
    """El fallo se registra pero la búsqueda continúa con el resto."""
    working_dto = MagicMock(external_id="as24-1", price=10000.0)

    async def _search(provider, query, **kwargs):
        if provider.name == "mobile_de":
            raise ProviderRateLimitError("429", provider="mobile_de")
        return [working_dto]

    mobile, as24 = MagicMock(name="mobile_de"), MagicMock(name="autoscout24")
    mobile.name, as24.name = "mobile_de", "autoscout24"
    registry = MagicMock()
    registry.get.side_effect = lambda n: mobile if n == "mobile_de" else as24

    vehicle_service = MagicMock()
    vehicle_service.search_from_provider = AsyncMock(side_effect=_search)

    orchestrator = _orchestrator(registry, vehicle_service)
    orchestrator._matches_filters = MagicMock(return_value=True)
    orchestrator._analyze_vehicle = AsyncMock(return_value=MagicMock())

    results = await orchestrator.search(
        SearchRequest(query="BMW", providers=["mobile_de", "autoscout24"])
    )

    assert len(results) == 1, "AS24 debe seguir aportando resultados"
    issues = orchestrator.last_provider_issues
    assert len(issues) == 1
    assert issues[0].provider == "mobile_de"


@pytest.mark.asyncio
async def test_analyze_failure_records_the_vehicle() -> None:
    """Si un DTO revienta el análisis, se identifica cuál."""
    dto = MagicMock(external_id="as24-99")
    vehicle_service = MagicMock()
    vehicle_service.search_from_provider = AsyncMock(return_value=[dto])

    orchestrator = _orchestrator(_registry_with(MagicMock()), vehicle_service)
    orchestrator._matches_filters = MagicMock(return_value=True)
    orchestrator._analyze_vehicle = AsyncMock(side_effect=ValueError("precio nulo"))

    results = await orchestrator.search(
        SearchRequest(query="BMW", providers=["autoscout24"])
    )

    assert results == []
    issue = orchestrator.last_provider_issues[0]
    assert issue.stage == "analyze"
    assert issue.external_id == "as24-99"
    assert "precio nulo" in issue.message


@pytest.mark.asyncio
async def test_issues_reset_between_searches() -> None:
    """No se arrastran fallos de una búsqueda anterior."""
    vehicle_service = MagicMock()
    vehicle_service.search_from_provider = AsyncMock(
        side_effect=ProviderConnectionError("403", provider="mobile_de")
    )
    orchestrator = _orchestrator(_registry_with(MagicMock()), vehicle_service)

    await orchestrator.search(SearchRequest(query="BMW", providers=["mobile_de"]))
    assert len(orchestrator.last_provider_issues) == 1

    vehicle_service.search_from_provider = AsyncMock(return_value=[])
    await orchestrator.search(SearchRequest(query="Audi", providers=["mobile_de"]))
    assert orchestrator.last_provider_issues == []


# ---------------------------------------------------------------------------
# Mensajes ES
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("error_type", "fragment"),
    [
        ("ProviderConnectionError", "anti-bot"),
        ("ProviderTimeoutError", "tardó demasiado"),
        ("ProviderRateLimitError", "rate limit"),
        ("ProviderParsingError", "no se pudo interpretar"),
        ("ProviderNotFoundError", "Revisa la marca"),
        ("KeyError", "no disponible"),
    ],
)
def test_known_errors_have_spanish_messages(error_type: str, fragment: str) -> None:
    message = provider_issue_message_es(
        provider="mobile_de", stage="search", error_type=error_type
    )

    assert fragment in message
    assert "mobile_de" in message


def test_unknown_error_falls_back_to_stage_message() -> None:
    """Nunca se muestra un mensaje vacío, aunque el error sea desconocido."""
    message = provider_issue_message_es(
        provider="autoscout24", stage="analyze", error_type="SomethingWeirdError"
    )

    assert message
    assert "autoscout24" in message


def test_payload_includes_spanish_message() -> None:
    issue = MagicMock(
        provider="mobile_de",
        stage="search",
        error_type="ProviderConnectionError",
        message="HTTP 403",
        external_id=None,
    )

    payload = build_provider_issue_payloads([issue])[0]

    assert payload["message"] == "HTTP 403"
    assert "anti-bot" in payload["message_es"]


def test_empty_issue_list_yields_empty_payload() -> None:
    assert build_provider_issue_payloads([]) == []
    assert build_provider_issue_payloads(None) == []
