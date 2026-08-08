from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text, Uuid
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.opportunity import Opportunity
    from app.models.user import User
    from app.models.vehicle import Vehicle


class DealStatus(str, Enum):
    """Estados del pipeline de gestión de un trato (Task D.1).

    NEW -> CONTACTED -> OFFER -> WON | LOST | DROPPED
    """

    NEW = "NEW"
    CONTACTED = "CONTACTED"
    OFFER = "OFFER"
    WON = "WON"
    LOST = "LOST"
    DROPPED = "DROPPED"


class Deal(Base):
    """Un trato en gestión: de la oportunidad al cierre.

    Conecta una oportunidad (y/o vehículo) con el pipeline de venta del
    usuario, permitiendo avanzar el estado (NEW -> CONTACTED -> OFFER ->
    WON/LOST/DROPPED) con notas, canal de contacto y precio de oferta.
    """

    __tablename__ = "deals"

    id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    """Dueño del trato (solo él puede verlo/gestionarlo)."""

    vehicle_id: Mapped[str | None] = mapped_column(
        Uuid(as_uuid=False),
        ForeignKey("vehicles.id", ondelete="SET NULL"),
        nullable=True,
    )
    """Vehículo asociado (opcional)."""

    opportunity_id: Mapped[str | None] = mapped_column(
        Uuid(as_uuid=False),
        ForeignKey("opportunities.id", ondelete="SET NULL"),
        nullable=True,
    )
    """Oportunidad de la que nace el trato (opcional)."""

    status: Mapped[DealStatus] = mapped_column(
        SAEnum(
            DealStatus,
            name="deal_status",
            values_callable=lambda e: [s.value for s in e],
        ),
        default=DealStatus.NEW,
        server_default=DealStatus.NEW.value,
        nullable=False,
    )
    """Estado actual del pipeline."""

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    """Notas internas sobre el trato."""

    offer_price: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    """Precio de la oferta (relevante en OFFER/WON)."""

    contact_channel: Mapped[str | None] = mapped_column(String(20), nullable=True)
    """Canal de contacto: email | phone | portal | other."""

    # ------------------------------------------------------------------
    # Última simulación de margen (Task E.2)
    # ------------------------------------------------------------------
    last_sim_purchase_price: Mapped[float | None] = mapped_column(
        Numeric(12, 2), nullable=True
    )
    """Precio de compra de la última simulación guardada."""

    last_sim_sale_price: Mapped[float | None] = mapped_column(
        Numeric(12, 2), nullable=True
    )
    """Precio de venta estimado de la última simulación guardada."""

    last_sim_total_cost: Mapped[float | None] = mapped_column(
        Numeric(12, 2), nullable=True
    )
    """Coste total de la última simulación guardada."""

    last_sim_net_profit: Mapped[float | None] = mapped_column(
        Numeric(12, 2), nullable=True
    )
    """Beneficio neto de la última simulación guardada."""

    last_sim_roi: Mapped[float | None] = mapped_column(
        Numeric(12, 2), nullable=True
    )
    """ROI (%) de la última simulación guardada."""

    last_sim_profile: Mapped[str | None] = mapped_column(String(20), nullable=True)
    """Perfil de costes de la última simulación guardada."""

    last_sim_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    """Fecha/hora en que se guardó la última simulación."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    user: Mapped[User] = relationship("User", back_populates="deals")
    vehicle: Mapped[Vehicle | None] = relationship("Vehicle", back_populates="deals")
    opportunity: Mapped[Opportunity | None] = relationship(
        "Opportunity", back_populates="deals"
    )

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        if getattr(self, "id", None) is None:
            self.id = str(uuid4())
        if getattr(self, "status", None) is None:
            self.status = DealStatus.NEW
        if getattr(self, "created_at", None) is None:
            self.created_at = datetime.now(UTC)
        if getattr(self, "updated_at", None) is None:
            self.updated_at = datetime.now(UTC)
