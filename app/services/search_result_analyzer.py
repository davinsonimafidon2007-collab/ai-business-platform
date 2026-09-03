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
        inspection_service: Any = None,
    ) -> None:
        self._vehicle_scorer = vehicle_scorer
        self._market_estimator = market_estimator
        self._profit_analyzer = profit_analyzer
        self._opportunity_finder = opportunity_finder
        self._negotiation_engine = negotiation_engine or NegotiationEngine()
        self._import_cost_profile = import_cost_profile
        self._inspection_service = inspection_service

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
        # 1. Mercado — prefiere estimate_async si existe y es corutina real,
        #    fallback a estimate. Solo se propaga comparable_providers cuando
        #    no es None, para mantener compatibilidad total con los
        #    callers/mocks existentes (default = registry o COMPARABLE_PROVIDERS
        #    de settings). Se calcula antes que el scoring (TASK 2 / AUD-007)
        #    para poder comparar el precio del vehículo contra el mercado.
        estimate_async = getattr(self._market_estimator, "estimate_async", None)
        has_async_estimate = estimate_async is not None and inspect.iscoroutinefunction(
            estimate_async
        )
        if comparable_providers:
            if has_async_estimate:
                market_estimation = await estimate_async(
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
            if has_async_estimate:
                market_estimation = await estimate_async(vehicle)
            else:
                result = self._market_estimator.estimate(vehicle)
                if inspect.iscoroutine(result):
                    market_estimation = await result
                else:
                    market_estimation = result

        # 2. Scoring — con el precio de mercado ya disponible, el componente
        #    de "precio competitivo" compara contra un dato real en vez de
        #    otorgar siempre el bono máximo (AUD-007).
        market_price_for_scoring = (
            market_estimation.market_price
            if market_estimation and market_estimation.market_price > 0
            else None
        )
        vehicle_score = self._vehicle_scorer.score(
            vehicle, market_price=market_price_for_scoring
        )

        # 3. Rentabilidad (usando el precio de reventa real estimado por el
        #    motor de mercado, en vez del multiplicador fijo por defecto, y
        #    el tipo de vendedor real del anuncio para el régimen fiscal
        #    correcto — AUD-008/AUD-009)
        estimated_sale_price = market_price_for_scoring
        market_grounded = estimated_sale_price is not None
        try:
            profit_analysis = self._profit_analyzer.analyze(
                vehicle,
                profile_name=self._import_cost_profile,
                estimated_sale_price=estimated_sale_price,
                seller_type=getattr(vehicle, "seller_type", None),
            )
        except ValueError as exc:
            # Null-safety (AUDIT.PARALLEL.1): vehículo sin precio/0 no debe
            # reventar el pipeline como si fuera un fallo de provider. Se
            # degrada a REJECT con análisis vacío y se sigue.
            logger.warning(
                "Vehículo sin precio válido; análisis de rentabilidad degradado "
                "a REJECT: %s",
                exc,
            )
            profit_analysis = self._fallback_profit_analysis(vehicle, exc)

        # 4. Oportunidad
        opportunity = self._opportunity_finder.analyze(
            vehicle_score,
            profit_analysis,
            market_estimation,
            market_grounded=market_grounded,
        )

        # 5. Estrategia de negociación — conecta datos de inspección reales si
        #    hay un InspectionService inyectado (flujo Search → Inspection).
        inspection_result = None
        if self._inspection_service is not None:
            inspection_result = await self._load_inspection_result(vehicle)

        negotiation_result = self.run_negotiation(
            vehicle=vehicle,
            vehicle_score=vehicle_score,
            market_estimation=market_estimation,
            profit_analysis=profit_analysis,
            inspection_result=inspection_result,
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
        inspection_result: InspectionResult | None = None,
    ) -> NegotiationInput:
        """Construye el NegotiationInput a partir de los análisis existentes.

        Reutiliza los modelos existentes (MarketEstimation, ProfitAnalysis,
        VehicleScore) sin duplicar lógica.

        ``inspection_result`` (opcional) permite conectar datos de inspección
        reales (p. ej. los generados por InspectionService) al motor de
        negociación. Si se omite, se usa un resultado vacío como fallback.
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

        # Inspección real (si se inyecta) o fallback vacío.
        # Conectar InspectionService → NegotiationEngine sin hardcodear defectos.
        inspection_result = inspection_result or InspectionResult(
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

    @staticmethod
    def _fallback_profit_analysis(vehicle: Any, reason: BaseException) -> Any:
        """ProfitAnalysis degradado para vehículos sin precio válido.

        Todos los valores a 0 y recomendación REJECT para que el vehículo
        aparezca en resultados como "no rentable" en vez de reventar el
        pipeline o clasificarse como fallo de provider.
        """
        from app.services.profit_analyzer import (
            CostBreakdown,
            ProfitAnalysis,
            ProfitRecommendation,
            RiskLevel,
        )

        return ProfitAnalysis(
            purchase_price=0.0,
            transport_cost=0.0,
            registration_cost=0.0,
            taxes=0.0,
            inspection_cost=0.0,
            repair_estimate=0.0,
            commission_cost=0.0,
            miscellaneous_cost=0.0,
            total_cost=0.0,
            estimated_sale_price=0.0,
            gross_profit=0.0,
            net_profit=0.0,
            roi_percentage=0.0,
            profit_margin_percentage=0.0,
            risk_level=RiskLevel.HIGH,
            recommendation=ProfitRecommendation.REJECT,
            cost_breakdown=CostBreakdown(
                purchase_price=0.0,
                transport_cost=0.0,
                registration_cost=0.0,
                taxes=0.0,
                inspection_cost=0.0,
                repair_estimate=0.0,
                commission_cost=0.0,
                miscellaneous_cost=0.0,
            ),
            warnings=[f"Sin precio válido: {reason}"],
        )

    def run_negotiation(
        self,
        vehicle: Any,
        vehicle_score: Any,
        market_estimation: Any,
        profit_analysis: Any,
        inspection_result: InspectionResult | None = None,
    ) -> NegotiationResult | None:
        """Ejecuta el motor de negociación si hay datos suficientes."""
        try:
            negotiation_input = self.build_negotiation_input(
                vehicle=vehicle,
                vehicle_score=vehicle_score,
                market_estimation=market_estimation,
                profit_analysis=profit_analysis,
                inspection_result=inspection_result,
            )
            return self._negotiation_engine.analyze(negotiation_input)
        except Exception:
            logger.exception("Error al ejecutar la negociación para el vehículo")
            return None

    async def _load_inspection_result(
        self, vehicle: Any
    ) -> InspectionResult | None:
        """Intenta obtener el InspectionResult real de un vehículo.

        Conecta el flujo Search → Inspection cuando hay un InspectionService
        inyectado. Si no hay sesión u observaciones, devuelve None (fallback
        a heurística en build_negotiation_input).
        """
        if self._inspection_service is None:
            return None
        try:
            session = await self._inspection_service.get_latest_session_for_vehicle(
                getattr(vehicle, "id", None)
            )
            if session is None:
                return None
            observations = await self._inspection_service.get_session_observations(
                session.id
            )
            if not observations:
                return None
            return self._inspection_service.build_inspection_result(observations)
        except Exception:
            logger.warning(
                "No se pudo cargar la inspección real del vehículo; "
                "usando heurística",
                exc_info=False,
            )
            return None
