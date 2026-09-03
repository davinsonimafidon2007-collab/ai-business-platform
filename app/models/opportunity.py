from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from sqlalchemy import DateTime, Float, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.deal import Deal
    from app.models.opportunity_phase import OpportunityPhase
    from app.models.vehicle import Vehicle


class OpportunityStatus(str, Enum):
    """Estado del ciclo de vida de la oportunidad en sí (TASK 3 / AUD-010).

    Distinto de ``recommendation`` (BUY_NOW/WATCH/NEGOTIATE/REJECT, la señal
    económica) y de un ``Deal.status`` (el pipeline de negociación/compra):
    ``status`` solo dice si la oportunidad sigue "abierta" para actuar sobre
    ella o si ya se convirtió en un deal.
    """

    OPEN = "OPEN"
    CONVERTED = "CONVERTED"


class Opportunity(Base):
    """Registro de una oportunidad de importación analizada.

    Almacena el resultado completo del análisis de oportunidad para
    un vehículo, incluyendo score, recomendación, ROI, riesgo y beneficio.
    """

    __tablename__ = "opportunities"

    id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    vehicle_id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False),
        ForeignKey("vehicles.id", ondelete="CASCADE"),
        nullable=False,
    )
    """Referencia al vehículo analizado."""

    opportunity_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    """Puntuación combinada de oportunidad (0-100)."""

    recommendation: Mapped[str | None] = mapped_column(String(50), nullable=True)
    """Recomendación de acción (BUY_NOW, WATCH, NEGOTIATE, REJECT)."""

    roi: Mapped[float | None] = mapped_column(Float, nullable=True)
    """Retorno sobre la inversión estimado (%)."""

    risk: Mapped[str | None] = mapped_column(String(20), nullable=True)
    """Nivel de riesgo (LOW, MEDIUM, HIGH)."""

    profit: Mapped[float | None] = mapped_column(Float, nullable=True)
    """Beneficio neto estimado (EUR)."""

    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    """Confianza 0-100 de la estimación (TASK 2, ver app/services/confidence.py).

    Concepto distinto de ``profit``/``roi`` (rentabilidad) y de ``risk``
    (riesgo): mide cuán fiables son los datos usados para el análisis, no
    cuánto se podría ganar ni cuán probable es que algo salga mal."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    """Momento en que se creó el registro."""

    analyzed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    """Momento en que se realizó el análisis de oportunidad."""

    engine_version: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )
    """Versión del motor de análisis que generó esta oportunidad (opcional)."""

    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=OpportunityStatus.OPEN.value
    )
    """Estado del ciclo de vida (OPEN/CONVERTED). Ver OpportunityStatus."""

    vehicle: Mapped[Vehicle] = relationship("Vehicle", back_populates="opportunities")
    deals: Mapped[list[Deal]] = relationship(
        "Deal",
        back_populates="opportunity",
    )
    phases: Mapped[list[OpportunityPhase]] = relationship(
        "OpportunityPhase",
        back_populates="opportunity",
        order_by="OpportunityPhase.order",
        cascade="all, delete-orphan",
    )

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        if getattr(self, "id", None) is None:
            self.id = str(uuid4())
        if getattr(self, "created_at", None) is None:
            self.created_at = datetime.now(UTC)
        if getattr(self, "status", None) is None:
            self.status = OpportunityStatus.OPEN.value

