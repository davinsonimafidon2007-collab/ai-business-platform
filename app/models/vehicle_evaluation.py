from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.negotiation import NegotiationResult

if TYPE_CHECKING:
    from app.models.vehicle import Vehicle


def _negotiation_default() -> None:
    """Valor por defecto para el campo negotiation como JSON."""
    return None


class VehicleEvaluation(Base):
    __tablename__ = "vehicle_evaluations"
    __table_args__ = (
        Index("ix_vehicle_evaluations_vehicle_id", "vehicle_id", unique=True),
    )

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    vehicle_id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False),
        ForeignKey("vehicles.id", ondelete="CASCADE"),
        nullable=False,
    )
    estimated_market_price_es: Mapped[float | None] = mapped_column(Float, nullable=True)
    estimated_import_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    estimated_registration_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    estimated_total_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    estimated_profit: Mapped[float | None] = mapped_column(Float, nullable=True)
    profit_margin_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    classification: Mapped[str | None] = mapped_column(String(10), nullable=True)
    warnings: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )
    # Almacenamos negotiation como JSON string en BD
    _negotiation: Mapped[str | None] = mapped_column(
        "negotiation", Text, nullable=True, default=None
    )

    vehicle: Mapped[Vehicle] = relationship("Vehicle", back_populates="evaluations")

    def __init__(self, **kwargs: Any) -> None:
        # Extraer negotiation antes de pasar a super() para evitar duplicación
        negotiation_value = kwargs.pop("negotiation", None)
        super().__init__(**kwargs)
        if getattr(self, "id", None) is None:
            self.id = str(uuid4())
        if getattr(self, "created_at", None) is None:
            self.created_at = datetime.now(UTC)
        if getattr(self, "updated_at", None) is None:
            self.updated_at = datetime.now(UTC)
        # Asignar negotiation después de la inicialización
        if negotiation_value is not None:
            self.negotiation = negotiation_value

    @property
    def negotiation(self) -> NegotiationResult | None:
        """Deserializa el JSON almacenado a NegotiationResult."""
        if self._negotiation is None:
            return None
        try:
            data = json.loads(self._negotiation)
            if isinstance(data, dict):
                # Reconstruir NegotiationResult desde dict
                from app.models.negotiation import (
                    NegotiationArgument,
                    NegotiationScript,
                )

                args_data = data.get("negotiation_arguments", [])
                args = [
                    NegotiationArgument(
                        argument=a.get("argument", ""),
                        economic_impact=a.get("economic_impact", 0.0),
                        category=a.get("category", "defect"),
                        severity=a.get("severity", 5),
                    )
                    for a in args_data
                ]

                script_data = data.get("negotiation_script", {})
                script = NegotiationScript(
                    opening=script_data.get("opening", ""),
                    defect_based_points=script_data.get("defect_based_points", []),
                    market_based_points=script_data.get("market_based_points", []),
                    closing=script_data.get("closing", ""),
                )

                from app.models.negotiation import NegotiationRecommendation

                rec_str = data.get("recommendation", "WALK_AWAY")
                try:
                    recommendation = NegotiationRecommendation(rec_str)
                except ValueError:
                    recommendation = NegotiationRecommendation.WALK_AWAY

                return NegotiationResult(
                    estimated_vehicle_value=data.get("estimated_vehicle_value", 0.0),
                    recommended_initial_offer=data.get("recommended_initial_offer", 0.0),
                    recommended_counter_offer=data.get("recommended_counter_offer", 0.0),
                    maximum_purchase_price=data.get("maximum_purchase_price", 0.0),
                    walk_away_price=data.get("walk_away_price", 0.0),
                    expected_profit=data.get("expected_profit", 0.0),
                    expected_roi=data.get("expected_roi", 0.0),
                    negotiation_arguments=args,
                    negotiation_script=script,
                    recommendation=recommendation,
                    leverage_score=data.get("leverage_score", 50.0),
                    price_gap=data.get("price_gap", 0.0),
                    discount_needed=data.get("discount_needed", 0.0),
                )
            return None
        except (json.JSONDecodeError, TypeError, ValueError):
            return None

    @negotiation.setter
    def negotiation(self, value: NegotiationResult | None) -> None:
        """Serializa NegotiationResult a JSON string para almacenamiento."""
        if value is None:
            self._negotiation = None
            return
        try:
            # Serializar NegotiationResult a dict usando dataclasses.asdict
            from dataclasses import asdict

            data = asdict(value)
            # Convertir Enum a string
            if "recommendation" in data and hasattr(data["recommendation"], "value"):
                data["recommendation"] = data["recommendation"].value
            self._negotiation = json.dumps(data, ensure_ascii=False)
        except (TypeError, ValueError):
            self._negotiation = None
