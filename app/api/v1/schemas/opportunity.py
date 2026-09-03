"""Pydantic schemas for the opportunities API (Task C.1)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, computed_field


class OpportunityVehicleSummary(BaseModel):
    """Resumen del vehículo asociado a una oportunidad."""

    id: str
    brand: str | None = None
    model: str | None = None
    year: int | None = None
    mileage: int | None = None
    price: float | None = None
    source: str | None = None
    external_id: str | None = None
    url: str | None = None


class OpportunityRead(BaseModel):
    """Oportunidad de importación lista para el frontend."""

    id: str
    vehicle: OpportunityVehicleSummary | None = None
    score: float | None = None
    estimated_profit: float | None = None
    roi_percentage: float | None = None
    recommendation: str | None = None
    risk_level: str | None = None
    confidence: float | None = Field(
        default=None,
        description=(
            "Confianza 0-100 de los datos usados (TASK 2): distinta de "
            "estimated_profit/roi (rentabilidad) y de risk_level (riesgo). "
            "Ver app/services/confidence.py."
        ),
    )
    recommendation_label_es: str = ""
    risk_label_es: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def recommendation_label(self) -> str:
        """Alias legible de recommendation_label_es (TEST.OPP.LABELS.1)."""
        return self.recommendation_label_es

    @computed_field  # type: ignore[prop-decorator]
    @property
    def risk_label(self) -> str:
        """Alias legible de risk_label_es (TEST.OPP.LABELS.1)."""
        return self.risk_label_es


class OpportunityListResponse(BaseModel):
    """Respuesta paginada del listado de oportunidades."""

    items: list[OpportunityRead]
    total: int
    limit: int
    offset: int


class OpportunityCreate(BaseModel):
    """Cuerpo para registrar una oportunidad manualmente (TASK-021).

    Solo exige ``vehicle_id`` (el vehículo debe pertenecer al usuario).
    El resto de campos son el resultado del análisis de oportunidad y se
    persisten tal cual (score, ROI, recomendación, riesgo, beneficio).
    """

    vehicle_id: str
    score: float | None = None
    estimated_profit: float | None = None
    roi_percentage: float | None = None
    recommendation: str | None = None
    risk_level: str | None = None
    engine_version: str | None = None


class OpportunityUpdate(BaseModel):
    """Cuerpo para actualizar una oportunidad (TASK-021).

    Solo los campos analíticos son editables; ``vehicle_id`` no se puede
    cambiar (el vínculo es inmutable).
    """

    score: float | None = None
    estimated_profit: float | None = None
    roi_percentage: float | None = None
    recommendation: str | None = None
    risk_level: str | None = None


class OpportunityPhaseRead(BaseModel):
    """Fase del workflow de una oportunidad."""

    id: str
    opportunity_id: str
    title: str
    description: str | None = None
    status: str
    agent: str | None = None
    order: int = 0
    started_at: datetime | None = None
    completed_at: datetime | None = None
    feedback: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class OpportunityReadDetail(OpportunityRead):
    """Oportunidad con detalle ampliado para la página de detalle."""

    phases: list[OpportunityPhaseRead] = []
