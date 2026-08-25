"""Schemas Pydantic de entrada/salida de los agents (AUDIT.AGENTS.1).

Cada agent declara su ``input_type`` y ``output_type`` aquí. Los schemas
son el contrato único de la capa de agents: validan la entrada antes de
ejecutar y serializan la salida.

Los outputs envuelven los resultados REALES de los services de dominio
(VehicleScorer, OpportunityFinder, NegotiationEngine, SearchEngineService);
no inventan datos.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

# =============================================================================
# SearchAgent
# =============================================================================


class SearchAgentInput(BaseModel):
    """Entrada del SearchAgent."""

    query: str = Field(..., min_length=1, description="Término de búsqueda")
    max_results: int = Field(20, ge=1, le=100)
    country: str = Field("ES", max_length=10)
    budget_max: float | None = Field(None, ge=0)
    providers: list[str] | None = Field(
        None, description="Providers concretos; None = defaults del SearchRequest"
    )


class SearchAgentOutput(BaseModel):
    """Salida del SearchAgent: resultado real del SearchEngineService."""

    summary: Any = Field(..., description="SearchSummary")
    results: list[Any] = Field(default_factory=list, description="SearchResult[]")
    provider_issues: list[Any] = Field(default_factory=list)

    model_config = {"arbitrary_types_allowed": True}


# =============================================================================
# ScoringAgent
# =============================================================================


class VehicleDataInput(BaseModel):
    """Campos del vehículo que consume VehicleScorer.score_from_dto."""

    price: float | None = Field(None, ge=0)
    mileage: int | None = Field(None, ge=0)
    year: int | None = Field(None, ge=1900)
    fuel_type: str | None = None
    transmission: str | None = None
    power_hp: int | None = Field(None, ge=0)
    description: str | None = None
    images: list[str] | None = None
    brand: str | None = None
    model: str | None = None


class ScoringAgentInput(BaseModel):
    """Entrada del ScoringAgent."""

    vehicle: VehicleDataInput


class ScoringAgentOutput(BaseModel):
    """Salida del ScoringAgent (VehicleScore serializado)."""

    score: int = Field(..., ge=0, le=100)
    category_key: str
    category_label_es: str
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)


class RescoreAgentInput(BaseModel):
    """Entrada para recalcular score tras un cambio de precio.

    Reemplaza al antiguo ReScoringAgent (duplicado del ScoringAgent).
    """

    vehicle_id: str = Field(..., min_length=1)
    new_price: float = Field(..., gt=0)
    vehicle: VehicleDataInput


class RescoreAgentOutput(BaseModel):
    """Salida del re-scoring: score nuevo vs. score con el precio anterior."""

    vehicle_id: str
    previous_price: float | None
    new_price: float
    previous_score: int = Field(..., ge=0, le=100)
    score: int = Field(..., ge=0, le=100)
    delta: float
    category_key: str
    category_label_es: str


# =============================================================================
# OpportunityAgent
# =============================================================================


class VehicleScoreData(BaseModel):
    """Subconjunto de VehicleScore que consume OpportunityFinder."""

    score: int = Field(0, ge=0, le=100)
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)


class ProfitAnalysisData(BaseModel):
    """Subconjunto de ProfitAnalysis que consume OpportunityFinder."""

    net_profit: float = 0.0
    roi_percentage: float = 0.0
    purchase_price: float = 0.0
    risk_level: str = "UNKNOWN"


class MarketEstimationData(BaseModel):
    """Subconjunto de MarketEstimation que consume OpportunityFinder."""

    market_price: float = 0.0
    confidence: float = Field(50.0, ge=0, le=100)
    supply_level: float = Field(50.0, ge=0, le=100)
    demand_level: float = Field(50.0, ge=0, le=100)
    market_trend: Literal["rising", "stable", "falling"] = "stable"


class OpportunityAgentInput(BaseModel):
    """Entrada del OpportunityAgent."""

    vehicle_score: VehicleScoreData
    profit_analysis: ProfitAnalysisData
    market_estimation: MarketEstimationData


class OpportunityAgentOutput(BaseModel):
    """Salida completa del análisis de oportunidad (OpportunityAnalysis)."""

    overall_score: float = Field(..., ge=0, le=100)
    opportunity_level: str
    recommendation: str
    estimated_profit: float
    roi: float
    market_confidence: float
    risk_level: str
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)


# =============================================================================
# NegotiationAgent
# =============================================================================


class DefectItemInput(BaseModel):
    """Defecto detectado en inspección (contrato de app.models.negotiation)."""

    category: str = "general"
    description: str = Field(..., min_length=1)
    severity: int = Field(5, ge=1, le=10)
    estimated_repair_cost: float = Field(0.0, ge=0)
    is_safety_relevant: bool = False
    can_be_used_as_leverage: bool = True


class RepairEstimateInput(BaseModel):
    """Estimación de costes de reparación."""

    total_repair_cost: float = Field(0.0, ge=0)
    parts_cost: float = Field(0.0, ge=0)
    labor_cost: float = Field(0.0, ge=0)
    paint_and_body_cost: float = Field(0.0, ge=0)
    diagnostic_cost: float = Field(0.0, ge=0)


class InspectionResultInput(BaseModel):
    """Resultado de inspección resumido."""

    defects: list[DefectItemInput] = Field(default_factory=list)
    overall_condition: int = Field(10, ge=1, le=10)
    has_accident_history: bool = False
    accident_notes: str = ""


class NegotiationAgentInput(BaseModel):
    """Entrada del NegotiationAgent (construye NegotiationInput internamente)."""

    inspection_result: InspectionResultInput = Field(default_factory=InspectionResultInput)
    repair_estimate: RepairEstimateInput = Field(default_factory=RepairEstimateInput)
    market_estimation: MarketEstimationData = Field(default_factory=MarketEstimationData)
    asking_price: float = Field(0.0, ge=0)
    minimum_desired_profit: float = Field(0.0, ge=0)
    target_margin: float = Field(15.0, ge=0, le=100)
    vehicle_score_data: VehicleScoreData = Field(default_factory=VehicleScoreData)
    profit_analysis_data: ProfitAnalysisData = Field(default_factory=ProfitAnalysisData)


class NegotiationArgumentOutput(BaseModel):
    argument: str
    economic_impact: float
    category: str
    severity: int


class NegotiationScriptOutput(BaseModel):
    opening: str = ""
    defect_based_points: list[str] = Field(default_factory=list)
    market_based_points: list[str] = Field(default_factory=list)
    closing: str = ""


class NegotiationAgentOutput(BaseModel):
    """Estrategia completa de negociación (NegotiationResult serializado)."""

    estimated_vehicle_value: float
    recommended_initial_offer: float
    recommended_counter_offer: float
    maximum_purchase_price: float
    walk_away_price: float
    expected_profit: float
    expected_roi: float
    recommendation: str
    leverage_score: float
    price_gap: float
    discount_needed: float
    negotiation_arguments: list[NegotiationArgumentOutput] = Field(default_factory=list)
    negotiation_script: NegotiationScriptOutput = Field(default_factory=NegotiationScriptOutput)


# =============================================================================
# AlertAgent
# =============================================================================


class AlertOpportunityInput(BaseModel):
    """Oportunidad a evaluar contra las reglas (formato API de oportunidad)."""

    opportunity_level: str = ""
    recommendation: str = ""
    estimated_profit: float | None = None
    roi: float | None = None


class AlertRulesInput(BaseModel):
    """Umbrales de alerta opcionales."""

    min_level: str | None = None
    min_profit: float | None = Field(None, ge=0)
    min_roi: float | None = None


class AlertAgentInput(BaseModel):
    """Entrada del AlertAgent."""

    opportunity: AlertOpportunityInput
    rules: AlertRulesInput = Field(default_factory=AlertRulesInput)


class AlertAgentOutput(BaseModel):
    """Alertas disparadas por las reglas configuradas."""

    triggered: bool
    alerts: list[str] = Field(default_factory=list)


# =============================================================================
# BudgetSearchAgent
# =============================================================================


class BudgetSearchAgentInput(BaseModel):
    """Entrada del BudgetSearchAgent."""

    total_budget: float = Field(..., gt=0, description="Capital total disponible (EUR)")
    query: str = Field("*", min_length=1)
    max_results: int = Field(30, ge=1, le=100)
    profit_margin_min: float = Field(
        500.0, ge=0, description="Beneficio neto mínimo postventa (EUR)"
    )
    country: str = Field("ES", max_length=10)


class BudgetSearchAgentOutput(BaseModel):
    """Salida del BudgetSearchAgent: presupuesto + búsqueda real filtrada."""

    status: Literal["ok", "budget_too_low"]
    total_budget: float
    max_purchase_price: float
    query: str
    results: list[Any] = Field(default_factory=list)
    summary: Any | None = None
    provider_issues: list[Any] = Field(default_factory=list)
    filtered_out_count: int = Field(
        0, ge=0, description="Resultados descartados por profit_margin_min"
    )

    model_config = {"arbitrary_types_allowed": True}
