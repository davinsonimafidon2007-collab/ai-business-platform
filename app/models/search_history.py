from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from sqlalchemy import DateTime, Float, ForeignKey, Integer, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class SearchHistory(Base):
    """Registro del historial de búsquedas ejecutadas.

    Almacena cada búsqueda realizada, incluyendo los providers usados,
    cantidad de resultados y tiempo de ejecución para auditoría y análisis.
    """

    __tablename__ = "search_history"

    id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    user_id: Mapped[str | None] = mapped_column(
        Uuid(as_uuid=False),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    """Dueño de la búsqueda. Nullable solo para filas legacy pre-migración."""
    query: Mapped[str] = mapped_column(Text, nullable=False)
    """Término de búsqueda utilizado (URL o texto)."""

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    """Momento exacto en que se ejecutó la búsqueda."""

    providers_used: Mapped[str | None] = mapped_column(Text, nullable=True)
    """Lista de providers utilizados (serializada como JSON string)."""

    results_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    """Número de resultados obtenidos."""

    execution_time: Mapped[float | None] = mapped_column(Float, nullable=True)
    """Tiempo total de ejecución de la búsqueda en segundos."""

    user: Mapped[User | None] = relationship("User", back_populates="search_histories")

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        if getattr(self, "id", None) is None:
            self.id = str(uuid4())
        if getattr(self, "timestamp", None) is None:
            self.timestamp = datetime.now(UTC)

