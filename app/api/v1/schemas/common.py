"""Common API schemas for domain objects (score, market, profit, opportunity).

These are stable API-facing DTOs, decoupled from internal dataclasses.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

# =============================================================================
# VehicleScore
# =============================================================================


class VehicleScoreSchema(BaseModel):
    """Puntuación del vehículo. Equivalente público de VehicleScore."""

    score: int = Field(..., description="Puntuación final 0-100", ge=0, le=100)
    category: str = Field(..., description="Categoría textual (legacy ES)")
    category_key: str = Field(
        "poor",
        description="excellent|very_good|good|acceptable|poor",
    )
    category_label_es: str = Field(
        "",
        description="Etiqueta ES (Excelente, Muy bueno, …)",
    )
    strengths: list[str] = Field(default_factory=list, description="Fortalezas")
    weaknesses: list[str] = Field(default_factory=list, description="Debilidades")


# =============================================================================
# MarketEstimation
# =============================================================================


class MarketEstimationSchema(BaseModel):
    """Estimación de mercado. Equivalente público de MarketEstimation."""

    market_price: float = Field(..., description="Precio estimado de mercado (EUR)")
    confidence: float = Field(
        ..., description="Confianza de la estimación 0-100", ge=0, le=100
    )
    supply_level: float = Field(
        50.0, description="Nivel de oferta 0-100", ge=0, le=100
    )
    demand_level: float = Field(
        50.0, description="Nivel de demanda 0-100", ge=0, le=100
    )
    market_trend: str = Field("stable", description="Tendencia del mercado")
    comparable_count: int = Field(0, description="Número de comparables", ge=0)
    notes: list[str] = Field(
        default_factory=list,
        description="Notas machine-readable (pares clave=valor)",
    )
    explanation: str = Field(
        "",
        description="Texto legible (ES) del diferencial de precio vs comparables (MKT.1/MKT.2)",
    )
    provider_sources: list[str] = Field(
        default_factory=list,
        description="Providers que aportaron comparables (ej. mobile_de, es_market_fixture)",
    )


# =============================================================================
# CostBreakdown
# =============================================================================


class CostLineSchema(BaseModel):
    """Línea individual del desglose de costes."""

    key: str = Field(..., description="Clave interna de la partida")
    label_es: str = Field(..., description="Etiqueta legible en español")
    amount: float = Field(..., description="Importe (EUR)")


class CostBreakdownSchema(BaseModel):
    """Desglose de costes de importación."""

    purchase_price: float = Field(..., description="Precio de compra (EUR)")
    transport_cost: float = Field(..., description="Coste de transporte (EUR)")
    registration_cost: float = Field(..., description="Coste de matriculación (EUR)")
    taxes: float = Field(..., description="Impuestos (EUR)")
    inspection_cost: float = Field(..., description="Coste de ITV (EUR)")
    repair_estimate: float = Field(..., description="Estimación de reparaciones (EUR)")
    commission_cost: float = Field(..., description="Comisión (EUR)")
    miscellaneous_cost: float = Field(..., description="Otros costes (EUR)")
    total_fixed_costs: float = Field(0.0, description="Total costes fijos (EUR)")
    total_variable_costs: float = Field(0.0, description="Total costes variables (EUR)")
    total_cost: float = Field(..., description="Coste total (EUR)")
    cost_lines: list[CostLineSchema] = Field(
        default_factory=list,
        description="Desglose legible ES (PROFIT.1)",
    )


# =============================================================================
# ProfitAnalysis
# =============================================================================


class ProfitAnalysisSchema(BaseModel):
    """Análisis económico de importación. Equivalente público de ProfitAnalysis."""

    purchase_price: float = Field(..., description="Precio de compra (EUR)")
    transport_cost: float = Field(..., description="Coste de transporte (EUR)")
    registration_cost: float = Field(..., description="Coste de matriculación (EUR)")
    taxes: float = Field(..., description="Impuestos (EUR)")
    inspection_cost: float = Field(..., description="Coste de ITV (EUR)")
    repair_estimate: float = Field(..., description="Estimación reparaciones (EUR)")
    commission_cost: float = Field(..., description="Comisión (EUR)")
    miscellaneous_cost: float = Field(..., description="Otros costes (EUR)")
    total_cost: float = Field(..., description="Coste total (EUR)")
    estimated_sale_price: float = Field(..., description="Precio de venta estimado (EUR)")
    gross_profit: float = Field(..., description="Beneficio bruto (EUR)")
    net_profit: float = Field(..., description="Beneficio neto (EUR)")
    roi_percentage: float = Field(..., description="ROI (%)")
    profit_margin_percentage: float = Field(..., description="Margen de beneficio (%)")
    risk_level: str = Field(..., description="Nivel de riesgo (LOW, MEDIUM, HIGH)")
    recommendation: str = Field(..., description="Recomendación (BUY, CONSIDER, REJECT)")
    recommendation_label_es: str = Field(
        default="",
        description="Etiqueta legible en español de la recomendación (REC.1)",
    )
    risk_label_es: str = Field(
        default="",
        description="Etiqueta legible en español del nivel de riesgo (REC.1)",
    )
    coherence_warnings: list[str] = Field(
        default_factory=list,
        description="Avisos de coherencia ES (ROI.1); no bloquean la respuesta",
    )
    cost_breakdown: CostBreakdownSchema = Field(..., description="Desglose detallado")


# =============================================================================
# OpportunityAnalysis
# =============================================================================


class OpportunityAnalysisSchema(BaseModel):
    """Análisis de oportunidad de importación. Equivalente público de OpportunityAnalysis."""

    overall_score: float = Field(
        ..., description="Puntuación combinada 0-100", ge=0, le=100
    )
    opportunity_level: str = Field(
        ..., description="Nivel de oportunidad (EXCELLENT, GOOD, AVERAGE, POOR, REJECT)"
    )
    recommendation: str = Field(
        ..., description="Recomendación (BUY_NOW, WATCH, NEGOTIATE, REJECT)"
    )
    estimated_profit: float = Field(..., description="Beneficio neto estimado (EUR)")
    roi: float = Field(..., description="Retorno sobre la inversión (%)")
    market_confidence: float = Field(
        ..., description="Confianza de mercado 0-100", ge=0, le=100
    )
    risk_level: str = Field(..., description="Nivel de riesgo")
    recommendation_label_es: str = Field(
        default="",
        description="Etiqueta legible en español de la recomendación (REC.1)",
    )
    risk_label_es: str = Field(
        default="",
        description="Etiqueta legible en español del nivel de riesgo (REC.1)",
    )
    strengths: list[str] = Field(default_factory=list, description="Fortalezas")

    weaknesses: list[str] = Field(default_factory=list, description="Debilidades")

