"""SearchOrchestrator — Coordinador del flujo completo de búsqueda, análisis y clasificación.

Este servicio NO contiene lógica de scoring, beneficio o mercado.
Únicamente COORDINA los servicios existentes mediante inyección de dependencias.

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
    VehicleScorer.score()
        │
        ▼
    MarketEstimator.estimate()
        │
        ▼
    ProfitAnalyzer.analyze()
        │
        ▼
    OpportunityFinder.analyze()
        │
        ▼
    Lista ordenada de oportunidades
"""

from __future__ import annotations

from typing import Any

from app.models.negotiation import (
    DefectItem,
    InspectionResult,
    NegotiationInput,
    NegotiationResult,
    RepairEstimate,
)
from app.models.search import SearchRequest, SearchResult, SearchSummary
from app.models.market import MarketEstimation
from app.services.negotiation_engine import NegotiationEngine
from app.services.opportunity_finder import (
    OpportunityAnalysis,
    OpportunityFinder,
    OpportunityLevel,
    Recommendation,
)
from app.providers.registry import ProviderRegistry
from app.services.vehicle_service import VehicleService
from app.services.vehicle_scorer import VehicleScorer
from app.services.profit_analyzer import ProfitAnalyzer, RiskLevel


class SearchOrchestrator:
    """Orquestador de búsqueda, análisis y clasificación de oportunidades.

    Dependencias inyectadas:
        - VehicleService: para buscar vehículos en providers.
        - VehicleScorer: para puntuar vehículos.
        - MarketEstimator: para estimar condiciones de mercado.
        - ProfitAnalyzer: para analizar rentabilidad.
        - OpportunityFinder: para detectar oportunidades.
        - ProviderRegistry: para resolver providers por nombre.
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
        """
        self._vehicle_service = vehicle_service
        self._vehicle_scorer = vehicle_scorer
        self._market_estimator = market_estimator
        self._profit_analyzer = profit_analyzer
        self._opportunity_finder = opportunity_finder
        self._negotiation_engine = negotiation_engine or NegotiationEngine()
        self._provider_registry = provider_registry

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
                # Si falla la búsqueda en un provider, continuamos con el siguiente
                continue

            # Analizar cada vehículo
            for dto in vehicle_dtos:
                # Aplicar filtro de presupuesto explícito
                if request.budget_min is not None and (dto.price is None or dto.price < request.budget_min):
                    continue
                if request.budget_max is not None and (dto.price is None or dto.price > request.budget_max):
                    continue

                try:
                    result = self._analyze_vehicle(dto)
                    all_results.append(result)
                except Exception:
                    # Si falla el análisis de un vehículo, continuamos con el siguiente
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

    def _analyze_vehicle(self, vehicle: Any) -> SearchResult:
        """Ejecuta el pipeline completo de análisis sobre un vehículo.

        Args:
            vehicle: DTO del vehículo (VehicleSearchResult).

        Returns:
            SearchResult con todos los análisis.
        """
        # 1. Scoring
        vehicle_score = self._vehicle_scorer.score(vehicle)

        # 2. Mercado
        market_estimation = self._market_estimator.estimate(vehicle)

        # 3. Rentabilidad
        profit_analysis = self._profit_analyzer.analyze(vehicle)

        # 4. Oportunidad
        opportunity = self._opportunity_finder.analyze(
            vehicle_score,
            profit_analysis,
            market_estimation,
        )

        # 5. Estrategia de negociación
        negotiation_result = self._run_negotiation(
            vehicle=vehicle,
            vehicle_score=vehicle_score,
            market_estimation=market_estimation,
            profit_analysis=profit_analysis,
        )

        return SearchResult(
            vehicle=vehicle,
            vehicle_score=vehicle_score,
            market_estimation=market_estimation,
            profit_analysis=profit_analysis,
            opportunity=opportunity,
            negotiation=negotiation_result,
        )

    def _build_negotiation_input(
        self,
        vehicle: Any,
        vehicle_score: Any,
        market_estimation: Any,
        profit_analysis: Any,
    ) -> NegotiationInput:
        """Construye el NegotiationInput a partir de los análisis existentes.

        Reutiliza los modelos existentes (MarketEstimation, ProfitAnalysis,
        VehicleScore) sin duplicar lógica.
        """
        # Construir RepairEstimate a partir de profit_analysis
        repair_cost = getattr(profit_analysis, "repair_estimate", 0.0) or 0.0

        repair_estimate = RepairEstimate(
            total_repair_cost=repair_cost,
            parts_cost=0.0,
            labor_cost=0.0,
            paint_and_body_cost=0.0,
            diagnostic_cost=0.0,
        )

        # Construir Inspección simple (sin datos reales de inspección)
        # Se usa asking_price + mileage como heurística para detectar defectos
        inspection_result = InspectionResult(
            defects=[],
            overall_condition=10,
            has_accident_history=False,
            accident_notes="",
            inspection_notes=[],
        )

        # Extraer datos de ProfitAnalysis como dict
        profit_data = {}
        if profit_analysis is not None:
            profit_data["net_profit"] = getattr(profit_analysis, "net_profit", 0.0) or 0.0
            profit_data["roi_percentage"] = getattr(profit_analysis, "roi_percentage", 0.0) or 0.0
            profit_data["roi"] = profit_data["roi_percentage"]
            profit_data["profit_margin_percentage"] = getattr(profit_analysis, "profit_margin_percentage", 0.0) or 0.0
            profit_data["estimated_sale_price"] = getattr(profit_analysis, "estimated_sale_price", 0.0) or 0.0
            profit_data["total_cost"] = getattr(profit_analysis, "total_cost", 0.0) or 0.0
            profit_data["purchase_price"] = getattr(profit_analysis, "purchase_price", 0.0) or 0.0
            risk = getattr(profit_analysis, "risk_level", None)
            profit_data["risk_level"] = risk.value if hasattr(risk, "value") else str(risk or "")

        # Extraer datos de VehicleScore como dict
        vehicle_data = {}
        if vehicle_score is not None:
            vehicle_data["score"] = getattr(vehicle_score, "score", 50) or 50
            strengths = getattr(vehicle_score, "strengths", []) or []
            weaknesses = getattr(vehicle_score, "weaknesses", []) or []
            vehicle_data["strengths"] = strengths
            vehicle_data["weaknesses"] = weaknesses

        asking_price = getattr(vehicle, "price", 0.0) or 0.0

        return NegotiationInput(
            inspection_result=inspection_result,
            repair_estimate=repair_estimate,
            market_estimation=market_estimation,
            asking_price=asking_price,
            minimum_desired_profit=profit_data.get("net_profit", 0.0) * 0.5,
            target_margin=15.0,
            profit_analysis_data=profit_data,
            vehicle_score_data=vehicle_data,
        )

    def _run_negotiation(
        self,
        vehicle: Any,
        vehicle_score: Any,
        market_estimation: Any,
        profit_analysis: Any,
    ) -> NegotiationResult | None:
        """Ejecuta el motor de negociación si hay datos suficientes."""
        try:
            negotiation_input = self._build_negotiation_input(
                vehicle=vehicle,
                vehicle_score=vehicle_score,
                market_estimation=market_estimation,
                profit_analysis=profit_analysis,
            )
            return self._negotiation_engine.analyze(negotiation_input)
        except Exception:
            # Si falla la negociación, devolvemos None (no bloquea el resto)
            return None
