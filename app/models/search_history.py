from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import DateTime, Float, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class SearchHistory(Base):
    """Registro del historial de búsquedas ejecutadas.

    Almacena cada búsqueda realizada, incluyendo los providers usados,
    cantidad de resultados y tiempo de ejecución para auditoría y análisis.
    """

    __tablename__ = "search_history"

    id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    query: Mapped[str] = mapped_column(Text, nullable=False)
    """Término de búsqueda utilizado (URL o texto)."""

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    """Momento exacto en que se ejecutó la búsqueda."""

    providers_used: Mapped[str | None] = mapped_column(Text, nullable=True)
    """Lista de providers utilizados (serializada como JSON string)."""

    results_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    """Número de resultados obtenidos."""

    execution_time: Mapped[float | None] = mapped_column(Float, nullable=True)
    """Tiempo total de ejecución de la búsqueda en segundos."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        if getattr(self, "id", None) is None:
            self.id = str(uuid4())
        if getattr(self, "timestamp", None) is None:
            self.timestamp = datetime.now(timezone.utc)

