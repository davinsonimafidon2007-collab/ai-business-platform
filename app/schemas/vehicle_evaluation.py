from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class VehicleEvaluationBase(BaseModel):
    vehicle_id: str
    estimated_market_price_es: float | None = None
    estimated_import_cost: float | None = None
    estimated_registration_cost: float | None = None
    estimated_total_cost: float | None = None
    estimated_profit: float | None = None
    profit_margin_percent: float | None = None
    score: int | None = Field(default=None, ge=0, le=100)
    classification: str | None = Field(default=None, max_length=10)
    warnings: str | None = None
    recommendation: str | None = None
    negotiation: dict[str, Any] | None = None


class VehicleEvaluationCreate(VehicleEvaluationBase):
    pass


class VehicleEvaluationRead(VehicleEvaluationBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    updated_at: datetime


class VehicleEvaluationUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    estimated_market_price_es: float | None = None
    estimated_import_cost: float | None = None
    estimated_registration_cost: float | None = None
    estimated_total_cost: float | None = None
    estimated_profit: float | None = None
    profit_margin_percent: float | None = None
    score: int | None = Field(default=None, ge=0, le=100)
    classification: str | None = Field(default=None, max_length=10)
    warnings: str | None = None
    recommendation: str | None = None
    negotiation: dict[str, Any] | None = None
