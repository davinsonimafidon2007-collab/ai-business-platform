"""Negotiation Agent: preparar estrategia de negociación de compra."""

from __future__ import annotations

from app.agents.base import BaseAgent
from app.agents.schemas import NegotiationAgentInput, NegotiationAgentOutput
from app.models.negotiation import (
    DefectItem,
    InspectionResult,
    NegotiationInput,
    RepairEstimate,
)
from app.services.negotiation_engine import NegotiationEngine


class _MarketEstimationShim:
    """Adaptador MarketEstimationData -> objeto duck-typed para NegotiationEngine."""

    def __init__(self, data: object) -> None:
        self.market_price = getattr(data, "market_price", 0.0)
        self.confidence = getattr(data, "confidence", 50.0)
        self.supply_level = getattr(data, "supply_level", 50.0)
        self.demand_level = getattr(data, "demand_level", 50.0)
        self.market_trend = getattr(data, "market_trend", "stable")


class NegotiationAgent(BaseAgent[NegotiationAgentInput, NegotiationAgentOutput]):
    """Agent del pipeline NEGOTIATE.

    Delega en NegotiationEngine (motor real de estrategia de negociación).
    La entrada es el schema tipado ``NegotiationAgentInput``; el agent construye
    los DTOs de dominio (NegotiationInput) y serializa el NegotiationResult.
    """

    name = "negotiation_agent"
    role = "negotiation"
    description = (
        "Genera la estrategia completa de negociación: ofertas recomendadas, "
        "argumentos por impacto económico y script a partir de la inspección."
    )
    input_type = NegotiationAgentInput
    output_type = NegotiationAgentOutput
    default_timeout_seconds = 10.0

    def __init__(
        self,
        engine: NegotiationEngine | None = None,
        timeout_seconds: float | None = None,
    ) -> None:
        super().__init__(timeout_seconds=timeout_seconds)
        self._engine = engine or NegotiationEngine()

    async def _execute(self, input_data: NegotiationAgentInput) -> NegotiationAgentOutput:
        negotiation_input = self._build_input(input_data)
        result = self._engine.analyze(negotiation_input)
        return NegotiationAgentOutput(
            estimated_vehicle_value=result.estimated_vehicle_value,
            recommended_initial_offer=result.recommended_initial_offer,
            recommended_counter_offer=result.recommended_counter_offer,
            maximum_purchase_price=result.maximum_purchase_price,
            walk_away_price=result.walk_away_price,
            expected_profit=result.expected_profit,
            expected_roi=result.expected_roi,
            recommendation=(
                result.recommendation.value
                if hasattr(result.recommendation, "value")
                else str(result.recommendation)
            ),
            leverage_score=result.leverage_score,
            price_gap=result.price_gap,
            discount_needed=result.discount_needed,
            negotiation_arguments=[
                {
                    "argument": arg.argument,
                    "economic_impact": arg.economic_impact,
                    "category": arg.category,
                    "severity": arg.severity,
                }
                for arg in result.negotiation_arguments
            ],
            negotiation_script={
                "opening": result.negotiation_script.opening,
                "defect_based_points": list(result.negotiation_script.defect_based_points),
                "market_based_points": list(result.negotiation_script.market_based_points),
                "closing": result.negotiation_script.closing,
            },
        )

    @staticmethod
    def _build_input(input_data: NegotiationAgentInput) -> NegotiationInput:
        inspection = InspectionResult(
            defects=[
                DefectItem(
                    category=d.category,
                    description=d.description,
                    severity=d.severity,
                    estimated_repair_cost=d.estimated_repair_cost,
                    is_safety_relevant=d.is_safety_relevant,
                    can_be_used_as_leverage=d.can_be_used_as_leverage,
                )
                for d in input_data.inspection_result.defects
            ],
            overall_condition=input_data.inspection_result.overall_condition,
            has_accident_history=input_data.inspection_result.has_accident_history,
            accident_notes=input_data.inspection_result.accident_notes,
        )
        repair = RepairEstimate(
            total_repair_cost=input_data.repair_estimate.total_repair_cost,
            parts_cost=input_data.repair_estimate.parts_cost,
            labor_cost=input_data.repair_estimate.labor_cost,
            paint_and_body_cost=input_data.repair_estimate.paint_and_body_cost,
            diagnostic_cost=input_data.repair_estimate.diagnostic_cost,
        )
        return NegotiationInput(
            inspection_result=inspection,
            repair_estimate=repair,
            market_estimation=_MarketEstimationShim(input_data.market_estimation),
            asking_price=input_data.asking_price,
            minimum_desired_profit=input_data.minimum_desired_profit,
            target_margin=input_data.target_margin,
            profit_analysis_data=input_data.profit_analysis_data.model_dump(),
            vehicle_score_data=input_data.vehicle_score_data.model_dump(),
        )
