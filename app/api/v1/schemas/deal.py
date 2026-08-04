"""Pydantic schemas for the deals API (Task D.1)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

from app.models.deal import DealStatus


class DealCreate(BaseModel):
    """Body de creación de un deal.

    Requiere al menos uno de ``opportunity_id`` o ``vehicle_id``.
    """

    opportunity_id: str | None = None
    vehicle_id: str | None = None
    notes: str | None = None
    contact_channel: str | None = None

    @field_validator("contact_channel")
    @classmethod
    def _validate_channel(cls, value: str | None) -> str | None:
        if value is None:
            return value
        allowed = {"email", "phone", "portal", "other"}
        normalized = value.strip().lower()
        if normalized not in allowed:
            raise ValueError(
                f"contact_channel must be one of {sorted(allowed)}"
            )
        return normalized

    @field_validator("opportunity_id", "vehicle_id")
    @classmethod
    def _strip_optional(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        return value or None


class DealUpdateStatus(BaseModel):
    """Body de transición de estado de un deal."""

    status: DealStatus
    notes: str | None = None
    offer_price: float | None = None


class DealRead(BaseModel):
    """Deal lista para el frontend."""

    id: str
    user_id: str
    vehicle_id: str | None = None
    opportunity_id: str | None = None
    status: DealStatus
    notes: str | None = None
    offer_price: float | None = None
    contact_channel: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class DealListResponse(BaseModel):
    """Respuesta paginada del listado de deals."""

    items: list[DealRead]
    total: int
    limit: int
    offset: int
