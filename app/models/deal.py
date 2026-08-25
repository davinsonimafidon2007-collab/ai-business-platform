from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    Uuid,
    func,
    text,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.opportunity import Opportunity
    from app.models.user import User
    from app.models.vehicle import Vehicle


class DealStatus(str, Enum):
    """Estados del pipeline de gestión de un trato.

    Máquina de estados (v2):

        NEW         -> ANALYZING | CANCELLED
        ANALYZING   -> NEGOTIATING | LOST | CANCELLED
        NEGOTIATING -> WON | LOST | CANCELLED
        WON / LOST / CANCELLED -> terminal (sin salida)
    """

    NEW = "NEW"
    ANALYZING = "ANALYZING"
    NEGOTIATING = "NEGOTIATING"
    WON = "WON"
    LOST = "LOST"
    CANCELLED = "CANCELLED"

    @property
    def is_terminal(self) -> bool:
        """True si el estado es final (WON, LOST o CANCELLED)."""
        return self in TERMINAL_STATUSES


#: Estados activos: un deal activo bloquea la creación de otro para la misma
#: oportunidad (único deal activo por opportunity/user).
ACTIVE_STATUSES: frozenset[DealStatus] = frozenset(
    {DealStatus.NEW, DealStatus.ANALYZING, DealStatus.NEGOTIATING}
)

#: Estados terminales: sin transiciones de salida.
TERMINAL_STATUSES: frozenset[DealStatus] = frozenset(
    {DealStatus.WON, DealStatus.LOST, DealStatus.CANCELLED}
)


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Deal(Base):
    """Un trato en gestión: de la oportunidad al cierre.

    Conecta una oportunidad (y/o vehículo) con el pipeline del usuario.
    El estado avanza por una máquina estricta (NEW -> ANALYZING ->
    NEGOTIATING -> WON/LOST/CANCELLED); cada cambio queda registrado en
    ``deal_status_history`` y en el audit log.

    Concurrencia: ``version`` implementa bloqueo optimista (dos escrituras
    simultáneas sobre la misma fila provocan ``StaleDataError``, traducido
    a 409 por el servicio).
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

    status_changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )
    """Fecha/hora del último cambio de estado."""

    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    """Fecha/hora de cierre (cuando se alcanzó un estado terminal)."""

    version: Mapped[int] = mapped_column(default=0, server_default=text("0"))
    """Columna de bloqueo optimista (version_id_col)."""

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    """Notas internas sobre el trato."""

    offer_price: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    """Precio de la oferta (relevante en NEGOTIATING/WON)."""

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

    last_sim_roi: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
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

    # Un solo deal activo por (user_id, opportunity_id), garantizado en BD.
    # Índice único parcial: solo aplica a filas con estado activo.
    __table_args__ = (
        Index(
            "uq_deals_active_per_opportunity",
            "user_id",
            "opportunity_id",
            unique=True,
            postgresql_where=text(
                f"status IN ({', '.join(repr(s.value) for s in ACTIVE_STATUSES)})"
            ),
            sqlite_where=text(
                f"status IN ({', '.join(repr(s.value) for s in ACTIVE_STATUSES)})"
            ),
        ),
    )

    __mapper_args__ = {"version_id_col": version}

    user: Mapped[User] = relationship("User", back_populates="deals")
    vehicle: Mapped[Vehicle | None] = relationship("Vehicle", back_populates="deals")
    opportunity: Mapped[Opportunity | None] = relationship(
        "Opportunity", back_populates="deals"
    )
    status_history: Mapped[list[DealStatusHistory]] = relationship(
        "DealStatusHistory",
        back_populates="deal",
        cascade="all, delete-orphan",
        order_by="DealStatusHistory.created_at",
    )

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        now = datetime.now(UTC)
        if getattr(self, "id", None) is None:
            self.id = str(uuid4())
        if getattr(self, "status", None) is None:
            self.status = DealStatus.NEW
        if getattr(self, "created_at", None) is None:
            self.created_at = now
        if getattr(self, "updated_at", None) is None:
            self.updated_at = now
        if getattr(self, "status_changed_at", None) is None:
            self.status_changed_at = now
        if getattr(self, "version", None) is None:
            self.version = 0


class DealStatusHistory(Base):
    """Registro inmutable de cada transición de estado de un deal.

    Auditoría fina: quién cambió el estado, desde qué estado a cuál,
    cuándo, con qué notas y precio de oferta. La fila de creación tiene
    ``from_status`` NULL y ``to_status='NEW'``.
    """

    __tablename__ = "deal_status_history"

    id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    deal_id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False),
        ForeignKey("deals.id", ondelete="CASCADE"),
        nullable=False,
    )
    from_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    to_status: Mapped[str] = mapped_column(String(20), nullable=False)
    changed_by_user_id: Mapped[str | None] = mapped_column(
        Uuid(as_uuid=False), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    offer_price: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
    )

    deal: Mapped[Deal] = relationship("Deal", back_populates="status_history")

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        if getattr(self, "id", None) is None:
            self.id = str(uuid4())
        if getattr(self, "created_at", None) is None:
            self.created_at = datetime.now(UTC)
