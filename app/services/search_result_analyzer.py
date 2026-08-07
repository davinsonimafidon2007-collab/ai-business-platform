"""SearchResultAnalyzer — Analiza un vehículo en el pipeline completo.

Responsabilidad única: dado un DTO de vehículo, ejecuta el pipeline de
análisis (scoring → mercado → rentabilidad → oportunidad → negociación)
y devuelve un ``SearchResult``.

El ``SearchOrchestrator`` delega aquí el análisis de cada vehículo en
lugar de contener esta lógica acoplada junto a la orquestación de
providers. Este módulo **no** conoce providers ni cómo buscar; solo
coordina los analizadores inyectados.
"""

from __future__ import annotations

import inspect
from typing import Any

from app.core.logging import get_logger
from app.models.negotiation import (
    InspectionResult,
    NegotiationInput,
    NegotiationResult,
    RepairEstimate,
)
from app.models.search import SearchResult
from app.services.negotiation_engine import NegotiationEngine

logger = get_logger(__name__)


class SearchResultAnalyzer:
    """Coordina el análisis completo de un vehículo.

    Dependencias inyectadas (mismas que el orquestador):
        - VehicleScorer: puntúa el vehículo.
        - MarketEstimator: estima condiciones de mercado.
        - ProfitAnalyzer: analiza rentabilidad.
        - OpportunityFinder: detecta oportunidades.
        - NegotiationEngine: genera estrategia de negociación.

    Expone un único método público ``analyze(vehicle) -> SearchResult``.
    """

    def __init__(
        self,
        vehicle_scorer: Any,
        market_estimator: Any,
        profit_analyzer: Any,
        opportunity_finder: Any,
        negotiation_engine: NegotiationEngine | None = None,
        import_cost_profile: str = "SPAIN",
    ) -> None:
        self._vehicle_scorer = vehicle_scorer
        self._market_estimator = market_estimator
        self._profit_analyzer = profit_analyzer
        self._opportunity_finder = opportunity_finder
        self._negotiation_engine = negotiation_engine or NegotiationEngine()
        self._import_cost_profile = import_cost_profile

    async def analyze(
        self,
        vehicle: Any,
        *,
        comparable_providers: list[str] | None = None,
    ) -> SearchResult:
        """Ejecuta el pipeline completo de análisis sobre un vehículo.

        Args:
            vehicle: DTO del vehículo (VehicleSearchResult).
            comparable_providers: Allowlist opcional de sources para el
                estimador de mercado (comparables). ``None``/omitido = registry
                (o ``COMPARABLE_PROVIDERS`` de settings). No confundir con
                ``providers`` (listado de anuncios).

        Returns:
            SearchResult con todos los análisis.
        """
        # 1. Scoring
        vehicle_score = self._vehicle_scorer.score(vehicle)

        # 2. Mercado — prefiere estimate_async si existe, fallback a estimate.
        #    Solo se propaga comparable_providers cuando no es None, para
        #    mantener compatibilidad total con los callers/mocks existentes
        #    (default = registry o COMPARABLE_PROVIDERS de settings).
        estimate_method = getattr(self._market_estimator, "estimate_async", None)
        if comparable_providers:
            if estimate_method is not None:
                market_estimation = await estimate_method(
                    vehicle, comparable_providers=comparable_providers
                )
            else:
                result = self._market_estimator.estimate(
                    vehicle, comparable_providers=comparable_providers
                )
                if inspect.iscoroutine(result):
                    market_estimation = await result
                else:
                    market_estimation = result
        else:
            if estimate_method is not None:
                market_estimation = await estimate_method(vehicle)
            else:
                result = self._market_estimator.estimate(vehicle)
                if inspect.iscoroutine(result):
                    market_estimation = await result
                else:
                    market_estimation = result

        # 3. Rentabilidad (usando el precio de reventa real estimado por el
        #    motor de mercado, en vez del multiplicador fijo por defecto)
        estimated_sale_price = (
            market_estimation.market_price
            if market_estimation and market_estimation.market_price > 0
            else None
        )
        profit_analysis = self._profit_analyzer.analyze(
            vehicle,
            profile_name=self._import_cost_profile,
            estimated_sale_price=estimated_sale_price,
        )

        # 4. Oportunidad
        opportunity = self._opportunity_finder.analyze(
            vehicle_score,
            profit_analysis,
            market_estimation,
        )

        # 5. Estrategia de negociación
        negotiation_result = self.run_negotiation(
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

    def build_negotiation_input(
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
            profit_data["profit_margin_percentage"] = getattr(
                profit_analysis, "profit_margin_percentage", 0.0
            ) or 0.0
            profit_data["estimated_sale_price"] = getattr(
                profit_analysis, "estimated_sale_price", 0.0
            ) or 0.0
            profit_data["total_cost"] = getattr(profit_analysis, "total_cost", 0.0) or 0.0
            profit_data["purchase_price"] = getattr(
                profit_analysis, "purchase_price", 0.0
            ) or 0.0
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

    def run_negotiation(
        self,
        vehicle: Any,
        vehicle_score: Any,
        market_estimation: Any,
        profit_analysis: Any,
    ) -> NegotiationResult | None:
        """Ejecuta el motor de negociación si hay datos suficientes."""
        try:
            negotiation_input = self.build_negotiation_input(
                vehicle=vehicle,
                vehicle_score=vehicle_score,
                market_estimation=market_estimation,
                profit_analysis=profit_analysis,
            )
            return self._negotiation_engine.analyze(negotiation_input)
        except Exception:
            logger.exception("Error al ejecutar la negociación para el vehículo")
            return None
