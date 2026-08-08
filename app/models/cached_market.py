from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import DateTime, Float, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class CachedMarketData(Base):
    """Datos de mercado cacheados para un vehículo externo.

    Almacena estimaciones de mercado identificadas por external_id y provider,
    sin depender de la existencia del vehículo en la tabla vehicles.
    Esto permite cachear comparables incluso antes de importar un vehículo.

    La clave de caché es la combinación de (external_id, provider, market_hash).
    """

    __tablename__ = "cached_market_data"

    id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    external_id: Mapped[str] = mapped_column(String(255), nullable=False)
    """Identificador externo del vehículo en el provider."""

    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    """Nombre del provider de origen (mobile_de, autoscout24, etc.)."""

    market_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    """Hash único de los parámetros de estimación para invalidación selectiva."""

    market_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    """Precio estimado de mercado (EUR)."""

    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    """Nivel de confianza de la estimación (0-100)."""

    supply_level: Mapped[float | None] = mapped_column(Float, nullable=True)
    """Nivel de oferta en el mercado (0-100)."""

    demand_level: Mapped[float | None] = mapped_column(Float, nullable=True)
    """Nivel de demanda en el mercado (0-100)."""

    market_trend: Mapped[str | None] = mapped_column(String(20), nullable=True)
    """Tendencia del mercado (rising, stable, falling)."""

    comparable_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    """Número de vehículos comparables encontrados."""

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    """Notas adicionales sobre la estimación (JSON)."""

    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    """Texto legible (ES) del diferencial de precio vs comparables."""

    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    """Momento en que expira esta caché (TTL)."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    """Momento en que se creó la entrada en caché."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        if getattr(self, "id", None) is None:
            self.id = str(uuid4())
        if getattr(self, "created_at", None) is None:
            self.created_at = datetime.now(UTC)

