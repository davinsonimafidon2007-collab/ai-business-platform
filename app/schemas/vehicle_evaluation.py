from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


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

    @field_validator("negotiation", mode="before")
    @classmethod
    def _coerce_negotiation(cls, v: Any) -> Any:
        # Model exposes NegotiationResult dataclass; convert to dict for schema.
        if v is None or isinstance(v, dict):
            return v
        # dataclass NegotiationResult -> dict via asdict
        try:
            from dataclasses import asdict, is_dataclass

            if is_dataclass(v):
                data = asdict(v)
                # Enum -> value
                if "recommendation" in data and hasattr(data["recommendation"], "value"):
                    data["recommendation"] = data["recommendation"].value
                return data
        except Exception:
            pass
        return v


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
