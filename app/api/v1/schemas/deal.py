"""Pydantic schemas for the deals API (Task D.1)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

from app.models.deal import DealStatus


class DealCreate(BaseModel):
    """Body de creación de un deal.

    Se puede vincular por ``vehicle_id`` interno o por ``source`` +
    ``external_id``. Si se envía el par `source` + `external_id` sin
    `vehicle_id`, el backend resuelve el vehículo del usuario antes de
    crear el deal.
    """

    opportunity_id: str | None = None
    vehicle_id: str | None = None
    source: str | None = None
    external_id: str | None = None
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
    """Body de transición de estado de un deal.

    Los campos de cumplimiento (TASK 3) solo se usan al transicionar al
    estado correspondiente: ``actual_purchase_price`` en BOUGHT,
    ``transport_carrier``/``transport_cost`` en IN_TRANSIT,
    ``registration_plate``/``registration_cost``/``actual_taxes`` en
    REGISTERED, y ``sale_price`` (obligatorio)/``buyer_name``/
    ``buyer_contact`` en SOLD.
    """

    status: DealStatus
    notes: str | None = None
    offer_price: float | None = None
    actual_purchase_price: float | None = None
    transport_carrier: str | None = None
    transport_cost: float | None = None
    registration_plate: str | None = None
    registration_cost: float | None = None
    actual_taxes: float | None = None
    sale_price: float | None = None
    buyer_name: str | None = None
    buyer_contact: str | None = None


class DealStatusHistoryEntry(BaseModel):
    """Entrada inmutable del historial de estados de un deal (auditoría)."""

    id: str
    deal_id: str
    from_status: str | None = None
    to_status: str
    changed_by_user_id: str | None = None
    notes: str | None = None
    offer_price: float | None = None
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class DealHistoryResponse(BaseModel):
    """Respuesta paginada del historial de estados de un deal."""

    items: list[DealStatusHistoryEntry]
    total: int
    limit: int
    offset: int


class DealSimulationUpdate(BaseModel):
    """Body para guardar la última simulación de margen en un deal (Task E.2).

    Es un subset del ``SimulateProfitResponse`` + ``profile_name``. No toca
    el estado del pipeline ni los campos de negociación.
    """

    purchase_price: float | None = None
    estimated_sale_price: float | None = None
    total_cost: float | None = None
    net_profit: float | None = None
    roi_percentage: float | None = None
    profile_name: str | None = None


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
    last_sim_purchase_price: float | None = None
    last_sim_sale_price: float | None = None
    last_sim_total_cost: float | None = None
    last_sim_net_profit: float | None = None
    last_sim_roi: float | None = None
    last_sim_profile: str | None = None
    last_sim_at: datetime | None = None
    status_changed_at: datetime | None = None
    closed_at: datetime | None = None
    version: int = 0
    # --- TASK 3: snapshot de negociación ---
    negotiation_initial_offer: float | None = None
    negotiation_max_price: float | None = None
    negotiation_walk_away_price: float | None = None
    negotiation_recommendation: str | None = None
    negotiation_snapshot_at: datetime | None = None
    # --- TASK 3: cumplimiento físico ---
    actual_purchase_price: float | None = None
    bought_at: datetime | None = None
    transport_carrier: str | None = None
    transport_cost: float | None = None
    transport_started_at: datetime | None = None
    transport_completed_at: datetime | None = None
    registration_plate: str | None = None
    registration_cost: float | None = None
    actual_taxes: float | None = None
    registered_at: datetime | None = None
    sale_price: float | None = None
    buyer_name: str | None = None
    buyer_contact: str | None = None
    sold_at: datetime | None = None
    actual_profit: float | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class DealListResponse(BaseModel):
    """Respuesta paginada del listado de deals."""

    items: list[DealRead]
    total: int
    limit: int
    offset: int


class DealVarianceResponse(BaseModel):
    """Comparación previsto (última simulación) vs. real de un deal."""

    deal_id: str
    status: str
    projected_purchase_price: float | None = None
    actual_purchase_price: float | None = None
    projected_sale_price: float | None = None
    actual_sale_price: float | None = None
    projected_total_cost: float | None = None
    actual_total_cost: float | None = None
    projected_net_profit: float | None = None
    actual_net_profit: float | None = None
    profit_variance: float | None = None
    projected_roi_percentage: float | None = None

    model_config = ConfigDict(from_attributes=True)


class PortfolioSummaryResponse(BaseModel):
    """Reporting de cartera: deals cerrados (real vs. previsto) + pipeline
    activo (previsto, aún no realizado)."""

    by_status: dict[str, int]
    sold_count: int
    sold_actual_profit_sum: float | None = None
    sold_projected_profit_sum: float | None = None
    profit_variance_sum: float | None = None
    total_revenue: float | None = None
    total_invested: float | None = None
    pipeline_count: int
    pipeline_projected_profit: float | None = None

    model_config = ConfigDict(from_attributes=True)
