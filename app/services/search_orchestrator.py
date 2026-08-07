"""SearchOrchestrator — Coordinador del flujo completo de búsqueda, análisis y clasificación.

Este servicio NO contiene lógica de scoring, beneficio o mercado.
Únicamente COORDINA los servicios existentes mediante inyección de dependencias.

La lógica de análisis de cada vehículo (scoring → mercado → rentabilidad →
oportunidad → negociación) vive en ``SearchResultAnalyzer``; el orquestador
delega en él a través de ``_analyze_vehicle``.

Flujo:
    Providers
        │
        ▼
    VehicleService.search_from_provider(...)
        │
        ▼
    Resultados normalizados
        │
        ▼
    SearchResultAnalyzer.analyze()   (scoring / mercado / profit / opportunity / negotiation)
        │
        ▼
    filter / sort / summarize
        │
        ▼
    Lista ordenada de oportunidades
"""

from __future__ import annotations

from typing import Any

from app.core.config import settings
from app.core.logging import get_logger
from app.models.search import SearchRequest, SearchResult, SearchSummary
from app.providers.registry import ProviderRegistry
from app.services.negotiation_engine import NegotiationEngine
from app.services.opportunity_finder import (
    OpportunityAnalysis,
    OpportunityFinder,
    OpportunityLevel,
)
from app.services.profit_analyzer import ProfitAnalyzer
from app.services.search_result_analyzer import SearchResultAnalyzer
from app.services.vehicle_scorer import VehicleScorer
from app.services.vehicle_service import VehicleService

logger = get_logger(__name__)


class SearchOrchestrator:
    """Orquestador de búsqueda, análisis y clasificación de oportunidades.

    Dependencias inyectadas:
        - VehicleService: para buscar vehículos en providers.
        - VehicleScorer: para puntuar vehículos.
        - MarketEstimator: para estimar condiciones de mercado.
        - ProfitAnalyzer: para analizar rentabilidad.
        - OpportunityFinder: para detectar oportunidades.
        - ProviderRegistry: para resolver providers por nombre.

    El análisis por vehículo se delega en un :class:`SearchResultAnalyzer`,
    que se construye con las mismas dependencias inyectadas.
    """

    def __init__(
        self,
        vehicle_service: VehicleService,
        vehicle_scorer: VehicleScorer,
        market_estimator: Any,
        profit_analyzer: ProfitAnalyzer,
        opportunity_finder: OpportunityFinder,
        negotiation_engine: NegotiationEngine | None = None,
        provider_registry: type[ProviderRegistry] = ProviderRegistry,
        import_cost_profile: str | None = None,
    ) -> None:
        """Inicializa el orquestador con todas las dependencias.

        Args:
            vehicle_service: Servicio de vehículos para búsquedas.
            vehicle_scorer: Motor de puntuación de vehículos.
            market_estimator: Estimador de mercado (implementa MarketEstimator protocol).
            profit_analyzer: Analizador de rentabilidad.
            opportunity_finder: Detector de oportunidades.
            negotiation_engine: Motor de estrategia de negociación (opcional).
            provider_registry: Registro de providers (clase, no instancia).
            import_cost_profile: Perfil de costes de importación (default SPAIN).
        """
        self._vehicle_service = vehicle_service
        self._vehicle_scorer = vehicle_scorer
        self._market_estimator = market_estimator
        self._profit_analyzer = profit_analyzer
        self._opportunity_finder = opportunity_finder
        self._negotiation_engine = negotiation_engine or NegotiationEngine()
        self._provider_registry = provider_registry
        self._import_cost_profile = (
            import_cost_profile
            or getattr(settings, "default_import_cost_profile", None)
            or "SPAIN"
        )
        self._analyzer = SearchResultAnalyzer(
            vehicle_scorer=vehicle_scorer,
            market_estimator=market_estimator,
            profit_analyzer=profit_analyzer,
            opportunity_finder=opportunity_finder,
            negotiation_engine=self._negotiation_engine,
            import_cost_profile=self._import_cost_profile,
        )

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    async def search(self, request: SearchRequest) -> list[SearchResult]:
        """Ejecuta una búsqueda completa sobre múltiples providers.

        Args:
            request: Parámetros de la búsqueda.

        Returns:
            Lista de SearchResult ordenada por opportunity.overall_score DESC.
        """
        all_results: list[SearchResult] = []

        for provider_name in request.providers:
            try:
                provider = self._provider_registry.get(provider_name)
            except KeyError:
                continue

            # Construir kwargs adicionales
            kwargs: dict[str, Any] = {}
            if request.country:
                kwargs["country"] = request.country
            if request.budget_min is not None:
                kwargs["budget_min"] = request.budget_min
            if request.budget_max is not None:
                kwargs["budget_max"] = request.budget_max

            # Buscar vehículos
            try:
                vehicle_dtos = await self._vehicle_service.search_from_provider(
                    provider, request.query, **kwargs
                )
            except Exception:
                logger.exception("Error al buscar en provider %s", provider_name)
                continue

            # Analizar cada vehículo
            for dto in vehicle_dtos:
                if not self._matches_filters(dto, request):
                    continue

                try:
                    result = await self._analyze_vehicle(dto)
                    all_results.append(result)
                except Exception:
                    logger.exception("Error al analizar vehículo %s", getattr(dto, "external_id", "unknown"))
                    continue

        # Limitar resultados
        if request.max_results > 0:
            all_results = all_results[: request.max_results]

        # Ordenar por defecto: opportunity score DESC
        return self.sort(all_results)

    @staticmethod
    def summarize(results: list[SearchResult]) -> SearchSummary:
        """Genera un resumen de los resultados agrupados por nivel de oportunidad.

        Args:
            results: Lista de resultados a resumir.

        Returns:
            SearchSummary con los conteos por categoría.
        """
        summary = SearchSummary(total_results=len(results))

        for r in results:
            opportunity = r.opportunity
            if not isinstance(opportunity, OpportunityAnalysis):
                summary.rejected += 1
                continue

            level = opportunity.opportunity_level
            if level == OpportunityLevel.EXCELLENT:
                summary.excellent += 1
            elif level == OpportunityLevel.GOOD:
                summary.good += 1
            elif level == OpportunityLevel.AVERAGE:
                summary.average += 1
            elif level == OpportunityLevel.POOR:
                summary.poor += 1
            else:
                summary.rejected += 1

        return summary

    @staticmethod
    def top(results: list[SearchResult], n: int = 10) -> list[SearchResult]:
        """Devuelve los N mejores resultados (ya deben estar ordenados).

        Args:
            results: Lista de resultados ordenados.
            n: Número de resultados a devolver.

        Returns:
            Lista con los primeros N resultados.
        """
        return results[:n]

    @staticmethod
    def filter(
        results: list[SearchResult],
        *,
        recommendation: str | None = None,
        opportunity_level: str | None = None,
        risk_level: str | None = None,
    ) -> list[SearchResult]:
        """Filtra los resultados por recomendación, nivel de oportunidad o riesgo.

        Args:
            results: Lista de resultados a filtrar.
            recommendation: Recomendación (BUY_NOW, WATCH, NEGOTIATE, REJECT).
            opportunity_level: Nivel de oportunidad (EXCELLENT, GOOD, AVERAGE, POOR, REJECT).
            risk_level: Nivel de riesgo (LOW, MEDIUM, HIGH).

        Returns:
            Lista filtrada de resultados.
        """
        filtered: list[SearchResult] = []

        for r in results:
            opp = r.opportunity
            profit = r.profit_analysis

            if recommendation is not None:
                opp_rec = getattr(opp, "recommendation", None)
                rec_value = opp_rec.value if hasattr(opp_rec, "value") else str(opp_rec or "")
                if rec_value.upper() != recommendation.upper():
                    continue

            if opportunity_level is not None:
                opp_level = getattr(opp, "opportunity_level", None)
                level_value = opp_level.value if hasattr(opp_level, "value") else str(opp_level or "")
                if level_value.upper() != opportunity_level.upper():
                    continue

            if risk_level is not None:
                profit_risk = getattr(profit, "risk_level", None)
                risk_value = profit_risk.value if hasattr(profit_risk, "value") else str(profit_risk or "")
                if risk_value.upper() != risk_level.upper():
                    continue

            filtered.append(r)

        return filtered

    @staticmethod
    def sort(
        results: list[SearchResult],
        *,
        by: str = "score",
        reverse: bool = True,
    ) -> list[SearchResult]:
        """Ordena los resultados por un campo determinado.

        Args:
            results: Lista de resultados a ordenar.
            by: Campo por el que ordenar (score, ROI, beneficio, precio, kilómetros, año).
            reverse: True para orden descendente, False para ascendente.

        Returns:
            Lista ordenada de resultados.
        """
        def _sort_key(r: SearchResult) -> tuple[float, float, float, float]:
            """Genera clave de ordenación por defecto.

            Orden por defecto:
                1. Opportunity Score DESC
                2. ROI DESC
                3. Beneficio DESC
                4. Vehicle Score DESC
            """
            opp = r.opportunity
            profit = r.profit_analysis
            vs = r.vehicle_score

            opp_score = getattr(opp, "overall_score", 0.0) or 0.0
            roi = getattr(profit, "roi_percentage", 0.0) or 0.0
            net_profit = getattr(profit, "net_profit", 0.0) or 0.0
            vehicle_score = getattr(vs, "score", 0) or 0

            return (opp_score, roi, net_profit, float(vehicle_score))

        if reverse:
            results_sorted = sorted(results, key=_sort_key, reverse=True)
        else:
            results_sorted = sorted(results, key=_sort_key)

        # Si se especifica un campo distinto, reordenar
        if by != "score":
            sort_map: dict[str, str] = {
                "ROI": "roi_percentage",
                "beneficio": "net_profit",
                "precio": "purchase_price",
                "kilómetros": "mileage",
                "kilometros": "mileage",
                "año": "year",
                "ano": "year",
            }
            attr_name = sort_map.get(by, by)

            def _alt_sort_key(r: SearchResult) -> float:
                opp = r.opportunity
                profit = r.profit_analysis
                vs = r.vehicle_score
                vehicle = r.vehicle

                # Buscar el atributo en profit, vehicle, opp o vehicle_score
                val = getattr(profit, attr_name, None)
                if val is None:
                    val = getattr(vehicle, attr_name, None)
                if val is None:
                    val = getattr(opp, attr_name, None)
                if val is None:
                    val = getattr(vs, attr_name, None)
                return float(val or 0.0)

            results_sorted = sorted(results_sorted, key=_alt_sort_key, reverse=reverse)

        return results_sorted

    # ------------------------------------------------------------------
    # Métodos internos
    # ------------------------------------------------------------------

    @staticmethod
    def _matches_filters(dto: Any, request: SearchRequest) -> bool:
        """Indica si un DTO cumple todos los filtros de la solicitud (CODE-001).

        Comportamiento idéntico al filtrado inline previo: si un filtro aplica
        y el DTO no lo cumple, se descarta. Si el filtro no aplica (None),
        no restringe.
        """
        # Presupuesto
        if request.budget_min is not None and (dto.price is None or dto.price < request.budget_min):
            return False
        if request.budget_max is not None and (dto.price is None or dto.price > request.budget_max):
            return False

        # Marca / modelo / año / km / combustible / transmisión
        if request.brand is not None and (dto.brand is None or dto.brand.lower() != request.brand.lower()):
            return False
        if request.model is not None and (dto.model is None or request.model.lower() not in dto.model.lower()):
            return False
        if request.min_year is not None and (dto.year is None or dto.year < request.min_year):
            return False
        if request.max_year is not None and (dto.year is None or dto.year > request.max_year):
            return False
        if request.min_mileage is not None and (dto.mileage is None or dto.mileage < request.min_mileage):
            return False
        if request.max_mileage is not None and (dto.mileage is None or dto.mileage > request.max_mileage):
            return False
        if request.fuel_type is not None and (dto.fuel_type is None or dto.fuel_type.lower() != request.fuel_type.lower()):
            return False
        if request.transmission is not None and (dto.transmission is None or dto.transmission.lower() != request.transmission.lower()):
            return False

        return True

    async def _analyze_vehicle(self, vehicle: Any) -> SearchResult:
        """Ejecuta el pipeline completo de análisis sobre un vehículo.

        Wrapper fino: delega en ``SearchResultAnalyzer`` (donde vive la
        lógica de scoring/mercado/rentabilidad/oportunidad/negociación).

        Args:
            vehicle: DTO del vehículo (VehicleSearchResult).

        Returns:
            SearchResult con todos los análisis.
        """
        return await self._analyzer.analyze(vehicle)

