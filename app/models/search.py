from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field
from sqlalchemy import DateTime, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


# =============================================================================
# Modelo SQLAlchemy (persistencia)
# =============================================================================


class Search(Base):
    __tablename__ = "searches"

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    country: Mapped[str] = mapped_column(String(10), nullable=False)
    brands: Mapped[str | None] = mapped_column(Text, nullable=True)
    models: Mapped[str | None] = mapped_column(Text, nullable=True)
    filters: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        if getattr(self, "id", None) is None:
            self.id = str(uuid4())
        if getattr(self, "created_at", None) is None:
            self.created_at = datetime.now(timezone.utc)


# =============================================================================
# Modelos Pydantic para SearchOrchestrator (sin persistencia directa)
# =============================================================================


class SearchRequest(BaseModel):
    """Petición de búsqueda completa.

    Attributes:
        query: Término de búsqueda (URL o texto).
        max_results: Número máximo de resultados a devolver.
        providers: Lista de providers a utilizar (ej: ["mobile_de", "autoscout24"]).
        country: País de destino para la importación.
        budget_min: Presupuesto mínimo (EUR).
        budget_max: Presupuesto máximo (EUR).
    """

    query: str = Field(..., min_length=1, description="Término de búsqueda")
    max_results: int = Field(default=20, ge=1, le=100, description="Máximo de resultados")
    providers: list[str] = Field(default_factory=lambda: ["mobile_de", "autoscout24"])
    country: str = Field(default="ES", max_length=10)
    budget_min: float | None = Field(default=None, ge=0)
    budget_max: float | None = Field(default=None, ge=0)


class SearchResult(BaseModel):
    """Resultado individual de una búsqueda orquestada.

    Contiene el vehículo junto con todos los análisis asociados:
    scoring, estimación de mercado, análisis de beneficio y oportunidad.
    """

    vehicle: Any = Field(..., description="VehicleSearchResult o Vehicle")
    vehicle_score: Any = Field(..., description="VehicleScore del scorer")
    market_estimation: Any = Field(..., description="MarketEstimation")
    profit_analysis: Any = Field(..., description="ProfitAnalysis")
    opportunity: Any = Field(..., description="OpportunityAnalysis")

    model_config = {"arbitrary_types_allowed": True}


class SearchSummary(BaseModel):
    """Resumen de una búsqueda orquestada.

    Agrupa los resultados por nivel de oportunidad.
    """

    total_results: int = 0
    excellent: int = 0
    good: int = 0
    average: int = 0
    poor: int = 0
    rejected: int = 0


class SearchEngineResult(BaseModel):
    """Resultado completo de una búsqueda del SearchEngineService.

    Contiene tanto el resumen como la lista completa de resultados analizados.
    """

    summary: SearchSummary
    results: list[SearchResult]

    model_config = {"arbitrary_types_allowed": True}
