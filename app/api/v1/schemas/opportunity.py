"""Pydantic schemas for the opportunities API (Task C.1)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


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
    recommendation_label_es: str = ""
    risk_label_es: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class OpportunityListResponse(BaseModel):
    """Respuesta paginada del listado de oportunidades."""

    items: list[OpportunityRead]
    total: int
    limit: int
    offset: int