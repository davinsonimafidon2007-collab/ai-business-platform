from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.user import User


def _default_search_providers() -> list[str]:
    """Providers por defecto para una búsqueda (AS24-first, CRIT.001).

    AutoScout24 (DE + ES) y los fixtures ES se consultan siempre; mobile.de
    solo si ``settings.enable_mobile_de`` (requiere proxy residencial, sino
    403 anti-bot desde IPs datacenter).
    """
    from app.core.config import settings

    providers = ["autoscout24", "autoscout24_es", "es_market_fixture", "coches_net_fixture"]
    if getattr(settings, "enable_mobile_de", True):
        providers.insert(0, "mobile_de")
    return providers


# =============================================================================
# Modelo SQLAlchemy (persistencia)
# =============================================================================


class Search(Base):
    __tablename__ = "searches"

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    country: Mapped[str] = mapped_column(String(10), nullable=False)
    brands: Mapped[str | None] = mapped_column(Text, nullable=True)
    models: Mapped[str | None] = mapped_column(Text, nullable=True)
    filters: Mapped[str | None] = mapped_column(Text, nullable=True)
    query: Mapped[str | None] = mapped_column(String(500), nullable=True)
    results_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    execution_time: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
    )

    user: Mapped[User] = relationship("User", back_populates="searches")

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        if getattr(self, "id", None) is None:
            self.id = str(uuid4())
        if getattr(self, "created_at", None) is None:
            self.created_at = datetime.now(UTC)


# =============================================================================
# Modelos Pydantic para SearchOrchestrator (sin persistencia directa)
# =============================================================================


class SearchRequest(BaseModel):
    """Petición de búsqueda completa.

    Attributes:
        query: Término de búsqueda (URL o texto).
        max_results: Número máximo de resultados a devolver (tamaño de página).
        offset: Desplazamiento dentro de la lista ordenada (paginación).
        sort_by: Campo de ordenación (score, ROI, beneficio, precio, kilómetros, año).
        sort_order: Dirección de ordenación (asc/desc).
        providers: Lista de providers a utilizar (ej: ["autoscout24", "mobile_de"]).
        country: País de destino para la importación.
        budget_min: Presupuesto mínimo (EUR).
        budget_max: Presupuesto máximo (EUR).
    """

    query: str = Field(..., min_length=1, description="Término de búsqueda")
    max_results: int = Field(default=20, ge=1, le=100, description="Máximo de resultados")
    offset: int = Field(default=0, ge=0, description="Desplazamiento para paginación")
    sort_by: str = Field(default="score", description="Campo de ordenación")
    sort_order: Literal["asc", "desc"] = Field(
        default="desc", description="Dirección de ordenación"
    )
    providers: list[str] = Field(
        default_factory=_default_search_providers,
        max_length=20,
        description="Providers a consultar (sin duplicados; se normalizan)",
    )
    country: str = Field(default="ES", max_length=10)
    budget_min: float | None = Field(default=None, ge=0)
    budget_max: float | None = Field(default=None, ge=0)
    brand: str | None = Field(default=None, description="Marca del vehículo")
    model: str | None = Field(default=None, description="Modelo del vehículo")
    min_year: int | None = Field(default=None, ge=1900, description="Año mínimo")
    max_year: int | None = Field(default=None, ge=1900, description="Año máximo")
    min_mileage: int | None = Field(default=None, ge=0, description="Km mínimos")
    max_mileage: int | None = Field(default=None, ge=0, description="Km máximos")
    fuel_type: str | None = Field(default=None, description="Tipo de combustible")
    transmission: str | None = Field(default=None, description="Tipo de transmisión")
    comparable_providers: list[str] | None = Field(
        default=None,
        description=(
            "Sources para la estimación de mercado (comparables). "
            "None = registry (o COMPARABLE_PROVIDERS en settings). "
            "No confundir con 'providers' (listado de anuncios)."
        ),
    )

    @field_validator("providers")
    @classmethod
    def _normalize_providers(cls, value: list[str]) -> list[str]:
        """Normaliza la lista de providers: trim, sin vacíos y sin duplicados.

        Un provider repetido duplicaría peticiones de red y luego sería
        deduplicado igualmente por (source, external_id); mejor eliminarlo
        antes de gastar el fetch.
        """
        normalized: list[str] = []
        seen: set[str] = set()
        for name in value:
            clean = (name or "").strip()
            if not clean or clean in seen:
                continue
            seen.add(clean)
            normalized.append(clean)
        return normalized


class SearchResult(BaseModel):
    """Resultado individual de una búsqueda orquestada.

    Contiene el vehículo junto con todos los análisis asociados:
    scoring, estimación de mercado, análisis de beneficio, oportunidad
    y estrategia de negociación.
    """

    vehicle: Any = Field(..., description="VehicleSearchResult o Vehicle")
    vehicle_score: Any = Field(..., description="VehicleScore del scorer")
    market_estimation: Any = Field(..., description="MarketEstimation")
    profit_analysis: Any = Field(..., description="ProfitAnalysis")
    opportunity: Any = Field(..., description="OpportunityAnalysis")
    negotiation: Any | None = Field(None, description="NegotiationResult")

    model_config = {"arbitrary_types_allowed": True}


class ProviderIssue(BaseModel):
    """Fallo de un provider durante la búsqueda (SEARCH.DIAG.1).

    El orquestador no aborta si un provider falla: sigue con los demás. Sin
    esto, una búsqueda con todos los providers caídos devolvía ``200`` con
    ``results: []``, indistinguible de "no hay coches que encajen". Ese fallo
    silencioso ya escondió un 404 real de AutoScout24 (E2E.MANUAL.PASS.1).
    """

    provider: str
    stage: Literal["registry", "search", "analyze"]
    """Dónde falló: resolver el provider, la búsqueda, o el análisis de un DTO."""
    error_type: str
    message: str
    external_id: str | None = None
    """Solo en ``stage="analyze"``: el vehículo concreto que no se pudo analizar."""


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
    provider_issues: list[ProviderIssue] = Field(default_factory=list)
    """Providers que fallaron. Vacío = todos respondieron (SEARCH.DIAG.1)."""
    total_matches: int = 0
    """Total de resultados que encajan ANTES de aplicar offset/max_results.

    Permite paginar sin perder la noción de cuántos hay en total."""
    providers_succeeded: list[str] = Field(default_factory=list)
    """Providers solicitados que respondieron sin error (trazabilidad)."""

    model_config = {"arbitrary_types_allowed": True}
