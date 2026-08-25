from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.deal import Deal
    from app.models.inspection import InspectionSession
    from app.models.opportunity import Opportunity
    from app.models.user import User
    from app.models.vehicle_evaluation import VehicleEvaluation


class Vehicle(Base):
    __tablename__ = "vehicles"
    # GRAVE.007/MED.009: el unique es por usuario, no global. Cada usuario puede
    # guardar el mismo anuncio (source + external_id) que otro; un mismo usuario
    # solo lo guarda una vez. Alineado con la migración l2m3n4o5p6q7.
    __table_args__ = (
        UniqueConstraint(
            "user_id", "source", "external_id", name="ix_vehicles_user_source_external"
        ),
        Index("ix_vehicles_vin", "vin"),
        Index("ix_vehicles_user_id", "user_id"),
        Index("ix_vehicles_created_at", "created_at"),
    )

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    external_id: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=True)
    brand: Mapped[str] = mapped_column(String(100), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    version: Mapped[str | None] = mapped_column(String(255), nullable=True)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mileage: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fuel_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    transmission: Mapped[str | None] = mapped_column(String(50), nullable=True)
    power_hp: Mapped[int | None] = mapped_column(Integer, nullable=True)
    displacement_cc: Mapped[int | None] = mapped_column(Integer, nullable=True)
    doors: Mapped[int | None] = mapped_column(Integer, nullable=True)
    color: Mapped[str | None] = mapped_column(String(50), nullable=True)
    emissions: Mapped[str | None] = mapped_column(String(50), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    seller_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    first_registration: Mapped[str | None] = mapped_column(String(50), nullable=True)
    price: Mapped[float | None] = mapped_column(Float, nullable=True)
    currency: Mapped[str | None] = mapped_column(String(10), nullable=True)
    vin: Mapped[str | None] = mapped_column(String(50), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # CRIT.004/GRAVE.005: alineado con la migración k3l4m5n6o7p8 (JSON array).
    # En Postgres la columna es JSON; SQLAlchemy la serializa a JSON en SQLite.
    # `equipment` sigue siendo Text (CSV) porque no hay migración que lo convierta.
    images: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    equipment: Mapped[str | None] = mapped_column(Text, nullable=True)
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

    user: Mapped[User] = relationship("User", back_populates="vehicles")
    evaluations: Mapped[list[VehicleEvaluation]] = relationship(
        "VehicleEvaluation",
        back_populates="vehicle",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    opportunities: Mapped[list[Opportunity]] = relationship(
        "Opportunity",
        back_populates="vehicle",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    deals: Mapped[list[Deal]] = relationship(
        "Deal",
        back_populates="vehicle",
        passive_deletes=True,
    )
    inspection_sessions: Mapped[list[InspectionSession]] = relationship(
        "InspectionSession",
        back_populates="vehicle",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        if getattr(self, "id", None) is None:
            self.id = str(uuid4())
        if getattr(self, "created_at", None) is None:
            self.created_at = datetime.now(UTC)
        if getattr(self, "updated_at", None) is None:
            self.updated_at = datetime.now(UTC)