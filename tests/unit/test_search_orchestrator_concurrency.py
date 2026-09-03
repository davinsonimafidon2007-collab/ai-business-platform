"""Tests SEARCH.ORCH.1 — concurrencia, timeouts, paginación y orden en el SearchOrchestrator.

Cubre:
    - Fetch de providers CONCURRENTE (wall time < suma de latencias).
    - Timeout por provider: expira → ProviderIssue(stage=search, TimeoutError)
      sin destruir los resultados de los demás providers.
    - Normalización/dedup de la lista de providers en SearchRequest.
    - Paginación por offset/max_results + last_total_matches.
    - sort_by/sort_order con alias y fallback determinista.
    - Fallo en análisis de un DTO no destruye el resto.
    - Trazabilidad available_in_sources formalizada en el DTO.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.search import SearchRequest, SearchResult
from app.providers.dto import VehicleSearchResult
from app.providers.registry import ProviderRegistry
from app.services.opportunity_finder import OpportunityAnalysis, OpportunityLevel
from app.services.opportunity_finder import Recommendation as OppRecommendation
from app.services.search_orchestrator import SearchOrchestrator

# =============================================================================
# Helpers
# =============================================================================


def _make_orchestrator(
    vehicle_service_mock: AsyncMock,
    overall_score_by_ext: dict[str, float] | None = None,
) -> tuple[SearchOrchestrator, MagicMock]:
    """Orquestador con analizadores stub que puntúan según external_id.

    Devuelve (orquestador, market_estimator) para aserciones.
    """
    scores = overall_score_by_ext or {}

    def _make_result(dto: Any) -> SearchResult:
        ext = getattr(dto, "external_id", "x")
        score = scores.get(ext, 75.0)
        return SearchResult(
            vehicle=dto,
            vehicle_score=MagicMock(score=70),
            market_estimation=MagicMock(),
            profit_analysis=MagicMock(roi_percentage=10.0, net_profit=1000.0),
            opportunity=OpportunityAnalysis(
                overall_score=float(score),
                opportunity_level=OpportunityLevel.GOOD,
                recommendation=OppRecommendation.WATCH,
                estimated_profit=1000.0,
                roi=10.0,
                market_confidence=70.0,
                risk_level="LOW",
            ),
        )

    analyzer = MagicMock()
    analyzer.analyze = AsyncMock(side_effect=lambda dto, **kwargs: _make_result(dto))

    estimator = MagicMock()
    orchestrator = SearchOrchestrator(
        vehicle_service=vehicle_service_mock,
        vehicle_scorer=MagicMock(),
        market_estimator=estimator,
        profit_analyzer=MagicMock(),
        opportunity_finder=MagicMock(),
    )
    # Inyectar analizador stub (el real depende de los 5 servicios).
    orchestrator._analyzer = analyzer
    return orchestrator, estimator


def _dto(source: str, ext_id: str, price: float | None = 15000.0) -> VehicleSearchResult:
    return VehicleSearchResult(
        source=source,
        external_id=ext_id,
        url=f"https://{source}.example.com/{ext_id}",
        brand="BMW",
        model="320d",
        year=2020,
        mileage=50000,
        price=price,
    )


@pytest.fixture
def registry_stub():
    """Registry con providers ficticios mobile_de/autoscout24."""
    with patch.object(
        ProviderRegistry,
        "get",
        side_effect=lambda name: MagicMock(source_name=name),
    ):
        yield ProviderRegistry


# =============================================================================
# Concurrencia
# =============================================================================


class TestConcurrentFetch:
    @pytest.mark.asyncio
    async def test_providers_fetched_concurrently(self, registry_stub) -> None:
        """3 providers con 150 ms de latencia cada uno → wall time << 450 ms."""
        vehicle_service = AsyncMock()

        async def _slow(provider, query, **kwargs):
            await asyncio.sleep(0.15)
            return [_dto(provider.source_name, f"{provider.source_name}-1")]

        vehicle_service.search_from_provider = AsyncMock(side_effect=_slow)
        orchestrator, _ = _make_orchestrator(vehicle_service)

        request = SearchRequest(
            query="bmw",
            max_results=10,
            providers=["p1", "p2", "p3"],
        )
        start = time.perf_counter()
        results = await orchestrator.search(request)
        elapsed = time.perf_counter() - start

        assert len(results) == 3
        # Secuencial sería >= 0.45s; concurrente debe rondar 0.15s.
        assert elapsed < 0.40, f"fetch no concurrente ({elapsed:.2f}s)"

    @pytest.mark.asyncio
    async def test_order_preserved_despite_completion_order(self, registry_stub) -> None:
        """El provider más lento que aparece primero conserva su posición."""
        vehicle_service = AsyncMock()

        async def _varying(provider, query, **kwargs):
            name = provider.source_name
            if name == "slow_first":
                await asyncio.sleep(0.05)
            return [_dto(name, f"{name}-1")]

        async def _fast(p, q, **kwargs):
            return await _varying(p, q, **kwargs)

        # p1 lento (50ms), p2/p3 rápidos: gather preserva el orden de tareas.
        delays = {"p1": 0.05, "p2": 0.0, "p3": 0.0}

        async def _side(provider, query, **kwargs):
            await asyncio.sleep(delays[provider.source_name])
            return [_dto(provider.source_name, f"{provider.source_name}-1")]

        vehicle_service.search_from_provider = AsyncMock(side_effect=_side)
        orchestrator, _ = _make_orchestrator(vehicle_service)

        request = SearchRequest(query="bmw", max_results=10, providers=["p1", "p2", "p3"])
        results = await orchestrator.search(request)

        assert [r.vehicle.source for r in results] == ["p1", "p2", "p3"]


# =============================================================================
# Timeout por provider
# =============================================================================


class TestProviderTimeout:
    @pytest.mark.asyncio
    async def test_timeout_records_issue_and_keeps_others(self, monkeypatch, registry_stub) -> None:
        from app.core.config import settings

        monkeypatch.setattr(settings, "search_provider_timeout", 0.05)
        vehicle_service = AsyncMock()

        async def _hanging(provider, query, **kwargs):
            if provider.source_name == "hungry":
                await asyncio.sleep(5.0)
            return [_dto(provider.source_name, f"{provider.source_name}-1")]

        vehicle_service.search_from_provider = AsyncMock(side_effect=_hanging)
        orchestrator, _ = _make_orchestrator(vehicle_service)

        request = SearchRequest(query="bmw", max_results=10, providers=["hungry", "healthy"])
        start = time.perf_counter()
        results = await orchestrator.search(request)
        elapsed = time.perf_counter() - start

        # No espera los 5 s del provider colgado.
        assert elapsed < 2.0
        # Los resultados del provider sano sobreviven.
        assert len(results) == 1
        assert results[0].vehicle.source == "healthy"
        # El timeout queda trazado como issue de stage search.
        issues = orchestrator.last_provider_issues
        assert len(issues) == 1
        assert issues[0].provider == "hungry"
        assert issues[0].stage == "search"
        assert issues[0].error_type == "TimeoutError"

    @pytest.mark.asyncio
    async def test_timeout_disabled_when_zero(self, monkeypatch, registry_stub) -> None:
        from app.core.config import settings

        monkeypatch.setattr(settings, "search_provider_timeout", 0.0)
        vehicle_service = AsyncMock()
        vehicle_service.search_from_provider.return_value = [_dto("mobile_de", "1")]
        orchestrator, _ = _make_orchestrator(vehicle_service)

        request = SearchRequest(query="bmw", max_results=10, providers=["mobile_de"])
        results = await orchestrator.search(request)
        assert len(results) == 1
        assert orchestrator.last_provider_issues == []


# =============================================================================
# Normalización de providers
# =============================================================================


class TestProvidersNormalization:
    def test_duplicates_removed_preserving_order(self) -> None:
        req = SearchRequest(query="x", providers=["autoscout24", "mobile_de", "autoscout24"])
        assert req.providers == ["autoscout24", "mobile_de"]

    def test_whitespace_stripped_and_empty_dropped(self) -> None:
        req = SearchRequest(query="x", providers=["  autoscout24 ", "", "   ", "mobile_de"])
        assert req.providers == ["autoscout24", "mobile_de"]

    def test_max_length_enforced(self) -> None:
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            SearchRequest(query="x", providers=[f"p{i}" for i in range(21)])

    @pytest.mark.asyncio
    async def test_duplicate_provider_fetched_once(self, registry_stub) -> None:
        vehicle_service = AsyncMock()
        vehicle_service.search_from_provider.return_value = [_dto("mobile_de", "1")]
        orchestrator, _ = _make_orchestrator(vehicle_service)

        request = SearchRequest(
            query="bmw", max_results=10, providers=["mobile_de", "mobile_de"]
        )
        results = await orchestrator.search(request)

        assert vehicle_service.search_from_provider.call_count == 1
        assert len(results) == 1


# =============================================================================
# Paginación y total_matches
# =============================================================================


class TestPagination:
    @pytest.mark.asyncio
    async def test_offset_slices_sorted_results(self, registry_stub) -> None:
        vehicle_service = AsyncMock()
        dtos = [_dto("mobile_de", str(i)) for i in range(10)]
        vehicle_service.search_from_provider.return_value = dtos
        orchestrator, _ = _make_orchestrator(
            vehicle_service, overall_score_by_ext={str(i): float(i * 10) for i in range(10)}
        )

        request = SearchRequest(
            query="bmw", max_results=3, offset=4, providers=["mobile_de"], sort_by="score"
        )
        results = await orchestrator.search(request)

        # Score DESC: ext 90,80,70... offset 4 → 50,40,30
        assert [r.vehicle.external_id for r in results] == ["5", "4", "3"]
        assert orchestrator.last_total_matches == 10

    @pytest.mark.asyncio
    async def test_offset_beyond_end_returns_empty_but_total_kept(self, registry_stub) -> None:
        vehicle_service = AsyncMock()
        vehicle_service.search_from_provider.return_value = [_dto("mobile_de", "1")]
        orchestrator, _ = _make_orchestrator(vehicle_service)

        request = SearchRequest(query="bmw", max_results=5, offset=10, providers=["mobile_de"])
        results = await orchestrator.search(request)

        assert results == []
        assert orchestrator.last_total_matches == 1

    @pytest.mark.asyncio
    async def test_default_no_pagination_returns_all_limited(self, registry_stub) -> None:
        vehicle_service = AsyncMock()
        vehicle_service.search_from_provider.return_value = [
            _dto("mobile_de", str(i)) for i in range(7)
        ]
        orchestrator, _ = _make_orchestrator(vehicle_service)

        request = SearchRequest(query="bmw", max_results=5, providers=["mobile_de"])
        results = await orchestrator.search(request)

        assert len(results) == 5
        assert orchestrator.last_total_matches == 7


# =============================================================================
# Ordenación
# =============================================================================


class TestSortWiring:
    @pytest.mark.asyncio
    async def test_sort_by_price_ascending(self, registry_stub) -> None:
        vehicle_service = AsyncMock()
        vehicle_service.search_from_provider.return_value = [
            _dto("mobile_de", "a", price=30000.0),
            _dto("mobile_de", "b", price=10000.0),
            _dto("mobile_de", "c", price=20000.0),
        ]
        orchestrator, _ = _make_orchestrator(vehicle_service)

        request = SearchRequest(
            query="bmw",
            max_results=10,
            providers=["mobile_de"],
            sort_by="price",
            sort_order="asc",
        )
        results = await orchestrator.search(request)

        assert [r.vehicle.price for r in results] == [10000.0, 20000.0, 30000.0]

    @pytest.mark.asyncio
    async def test_sort_by_roi_desc_alias(self, registry_stub) -> None:
        vehicle_service = AsyncMock()
        vehicle_service.search_from_provider.return_value = [
            _dto("mobile_de", "a"),
            _dto("mobile_de", "b"),
            _dto("mobile_de", "c"),
        ]

        def _result_for(dto):
            rois = {"a": 5.0, "b": 25.0, "c": 12.0}
            return SearchResult(
                vehicle=dto,
                vehicle_score=MagicMock(score=70),
                market_estimation=MagicMock(),
                profit_analysis=MagicMock(
                    roi_percentage=rois[dto.external_id], net_profit=100.0
                ),
                opportunity=MagicMock(overall_score=50.0),
            )

        analyzer = MagicMock()
        analyzer.analyze = AsyncMock(side_effect=lambda dto, **kw: _result_for(dto))
        orchestrator, _ = _make_orchestrator(vehicle_service)
        orchestrator._analyzer = analyzer

        request = SearchRequest(
            query="bmw",
            max_results=10,
            providers=["mobile_de"],
            sort_by="roi",
            sort_order="desc",
        )
        results = await orchestrator.search(request)

        assert [r.profit_analysis.roi_percentage for r in results] == [25.0, 12.0, 5.0]

    @pytest.mark.asyncio
    async def test_unknown_sort_by_falls_back_to_score(self, registry_stub) -> None:
        vehicle_service = AsyncMock()
        dtos = [_dto("mobile_de", str(i)) for i in range(4)]
        vehicle_service.search_from_provider.return_value = dtos
        orchestrator, _ = _make_orchestrator(
            vehicle_service, overall_score_by_ext={str(i): float(i * 10) for i in range(4)}
        )

        request = SearchRequest(
            query="bmw",
            max_results=10,
            providers=["mobile_de"],
            sort_by="campo_inexistente",
        )
        results = await orchestrator.search(request)

        # Fallback: score DESC → 30,20,10,0
        assert [r.opportunity.overall_score for r in results] == [30.0, 20.0, 10.0, 0.0]


# =============================================================================
# Errores parciales de análisis
# =============================================================================


class TestPartialAnalysisFailure:
    @pytest.mark.asyncio
    async def test_one_bad_dto_does_not_kill_batch(self, registry_stub) -> None:
        vehicle_service = AsyncMock()
        good = _dto("mobile_de", "good")
        bad = _dto("mobile_de", "bad")
        vehicle_service.search_from_provider.return_value = [good, bad]

        analyzer = MagicMock()

        async def _analyze(dto, **kwargs):
            if dto.external_id == "bad":
                raise ValueError("boom")
            return SearchResult(
                vehicle=dto,
                vehicle_score=MagicMock(score=70),
                market_estimation=MagicMock(),
                profit_analysis=MagicMock(),
                opportunity=MagicMock(overall_score=60.0),
            )

        analyzer.analyze = AsyncMock(side_effect=_analyze)
        orchestrator, _ = _make_orchestrator(vehicle_service)
        orchestrator._analyzer = analyzer

        request = SearchRequest(query="bmw", max_results=10, providers=["mobile_de"])
        results = await orchestrator.search(request)

        assert len(results) == 1
        assert results[0].vehicle.external_id == "good"
        issues = orchestrator.last_provider_issues
        assert len(issues) == 1
        assert issues[0].stage == "analyze"
        assert issues[0].external_id == "bad"


# =============================================================================
# Trazabilidad cross-source
# =============================================================================


class TestTraceability:
    @pytest.mark.asyncio
    async def test_available_in_sources_formalized_on_real_dto(self, registry_stub) -> None:
        """El mismo coche en DE y ES → ES conservado y etiquetado en el DTO."""
        vehicle_service = AsyncMock()
        es = VehicleSearchResult(
            source="autoscout24_es",
            external_id="999",
            url="https://www.autoscout24.es/x/999",
            brand="BMW",
            model="320d",
            price=20000.0,
        )
        de = VehicleSearchResult(
            source="autoscout24",
            external_id="999",
            url="https://www.autoscout24.de/x/999",
            brand="BMW",
            model="320d",
            price=19500.0,
        )
        vehicle_service.search_from_provider.side_effect = lambda p, q, **kw: (
            [es] if p.source_name == "autoscout24_es" else [de]
        )
        orchestrator, _ = _make_orchestrator(vehicle_service)

        request = SearchRequest(
            query="bmw",
            max_results=10,
            providers=["autoscout24_es", "autoscout24"],
        )
        results = await orchestrator.search(request)

        assert len(results) == 1
        kept = results[0].vehicle
        assert isinstance(kept, VehicleSearchResult)
        assert kept.source == "autoscout24_es"
        assert kept.available_in_sources == ["autoscout24", "autoscout24_es"]

    @pytest.mark.asyncio
    async def test_single_source_listing_has_null_traceability(self, registry_stub) -> None:
        vehicle_service = AsyncMock()
        vehicle_service.search_from_provider.return_value = [
            _dto("mobile_de", "solo")
        ]
        orchestrator, _ = _make_orchestrator(vehicle_service)

        request = SearchRequest(query="bmw", max_results=10, providers=["mobile_de"])
        results = await orchestrator.search(request)

        assert results[0].vehicle.available_in_sources is None
