"""SearchOrder — Orden de búsqueda en background (PERSONAL.NOAUTH).

Una orden de búsqueda se crea con un query y (opcionalmente) un presupuesto
total de la operación. Un job del scheduler la procesa en segundo plano:
cuando encuentra vehículos los persiste y suma a ``new_count``. El frontend
muestra un badge "X nuevos" sumando ``new_count`` de las órdenes del usuario
y los limpia al marcarlos como vistos.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
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
    from app.models.user import User
    from app.models.vehicle import Vehicle


class SearchOrder(Base):
    """Orden de búsqueda en segundo plano."""

    __tablename__ = "search_orders"

    id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    query: Mapped[str] = mapped_column(String(500), nullable=False)
    total_budget: Mapped[float | None] = mapped_column(Float, nullable=True)
    """Capital total de la operación (EUR). Determina max_purchase_price."""
    max_purchase_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    """Precio máx. de compra derivado del presupuesto (import_cost profile)."""
    filters: Mapped[str | None] = mapped_column(Text, nullable=True)
    """Filtros de búsqueda adicionales (JSON serializado)."""
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    """PENDING | RUNNING | COMPLETED | FAILED"""
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    """Intentos de procesamiento. Una orden FAILED con ``attempts`` >=
    ``search_order_max_attempts`` se abandona (no se reintenta cada ciclo)."""
    results_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    """Vehículos totales encontrados por esta orden."""
    new_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    """No marcados como vistos por el usuario (badge)."""
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_run_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
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

    user: Mapped[User] = relationship("User", back_populates="search_orders")
    vehicles: Mapped[list[SearchOrderVehicle]] = relationship(
        "SearchOrderVehicle",
        back_populates="order",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __init__(self, **kwargs: Any) -> None:
        # Aceptar filters como dict y serializarlo
        filters_value = kwargs.pop("filters", None)
        super().__init__(**kwargs)
        if getattr(self, "id", None) is None:
            self.id = str(uuid4())
        if getattr(self, "created_at", None) is None:
            self.created_at = datetime.now(UTC)
        if getattr(self, "updated_at", None) is None:
            self.updated_at = datetime.now(UTC)
        if filters_value is not None:
            self.filters = (
                json.dumps(filters_value, ensure_ascii=False)
                if isinstance(filters_value, dict)
                else filters_value
            )

    def filters_dict(self) -> dict[str, Any]:
        """Deserializa ``filters`` (JSON) a dict."""
        if not self.filters:
            return {}
        try:
            data = json.loads(self.filters)
            return data if isinstance(data, dict) else {}
        except (json.JSONDecodeError, TypeError):
            return {}


class SearchOrderVehicle(Base):
    """Vehículo encontrado por una orden de búsqueda + estado "visto"."""

    __tablename__ = "search_order_vehicles"
    # Nota: search_order_id y vehicle_id ya generan sus índices vía
    # index=True en las columnas; declararlos también aquí duplicaba el
    # CREATE INDEX (mismo nombre) y rompía metadata.create_all.
    __table_args__ = (
        UniqueConstraint("search_order_id", "vehicle_id", name="uq_search_order_vehicle"),
    )

    id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    search_order_id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False),
        ForeignKey("search_orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    vehicle_id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False),
        ForeignKey("vehicles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    seen: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    result_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    """Snapshot serializado del SearchResultItem (para la UI del detalle)."""
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
    )

    order: Mapped[SearchOrder] = relationship(
        "SearchOrder", back_populates="vehicles"
    )
    vehicle: Mapped[Vehicle] = relationship("Vehicle")

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        if getattr(self, "id", None) is None:
            self.id = str(uuid4())
        if getattr(self, "created_at", None) is None:
            self.created_at = datetime.now(UTC)
