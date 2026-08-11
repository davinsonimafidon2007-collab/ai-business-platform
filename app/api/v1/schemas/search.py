"""Search endpoint schemas.

The request schema maps `min_price`/`max_price` (API-facing) to
`budget_min`/`budget_max` (internal SearchRequest) transparently.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

from app.api.v1.schemas.common import (
    MarketEstimationSchema,
    OpportunityAnalysisSchema,
    ProfitAnalysisSchema,
    VehicleScoreSchema,
)
from app.api.v1.schemas.negotiation import NegotiationResultSchema
from app.models.search import SearchRequest, _default_search_providers

# =============================================================================
# Request
# =============================================================================


class SearchAPIRequest(BaseModel):
    """Petición de búsqueda de vehículos.

    Attributes:
        query: Término de búsqueda (marca, modelo, etc.).
        providers: Lista de proveedores a consultar.
        max_results: Número máximo de resultados.
        min_price: Precio mínimo (EUR). Se mapea internamente a budget_min.
        max_price: Precio máximo (EUR). Se mapea internamente a budget_max.
    """

    query: str = Field(..., min_length=1, description="Término de búsqueda")
    providers: list[str] = Field(
        default_factory=_default_search_providers,
        description="Proveedores a consultar",
    )
    max_results: int = Field(
        default=30, ge=1, le=100, description="Máximo de resultados"
    )
    min_price: float | None = Field(
        default=None, ge=0, description="Precio mínimo (EUR)"
    )
    max_price: float | None = Field(
        default=None, ge=0, description="Precio máximo (EUR)"
    )
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
            "Sources para estimación de mercado (comparables). "
            "None/omitido = registry (o COMPARABLE_PROVIDERS en settings). "
            "No confundir con 'providers' (listado de anuncios)."
        ),
    )

    def to_search_request(self) -> SearchRequest:
        """Convierte esta petición API al modelo interno SearchRequest.

        Mapea min_price → budget_min y max_price → budget_max.
        """
        return SearchRequest(
            query=self.query,
            max_results=self.max_results,
            providers=self.providers,
            budget_min=self.min_price,
            budget_max=self.max_price,
            brand=self.brand,
            model=self.model,
            min_year=self.min_year,
            max_year=self.max_year,
            min_mileage=self.min_mileage,
            max_mileage=self.max_mileage,
            fuel_type=self.fuel_type,
            transmission=self.transmission,
            comparable_providers=self.comparable_providers,
        )

    @model_validator(mode="after")
    def _validate_price_range(self) -> SearchAPIRequest:
        """Valida que min_price <= max_price si ambos están presentes."""
        if (
            self.min_price is not None
            and self.max_price is not None
            and self.min_price > self.max_price
        ):
            raise ValueError("min_price must be less than or equal to max_price")
        return self


# =============================================================================
# Response
# =============================================================================


class SearchSummarySchema(BaseModel):
    """Resumen de la búsqueda agrupado por nivel de oportunidad."""

    total_results: int = Field(0, description="Total de resultados")
    excellent: int = Field(0, description="Oportunidades excelentes")
    good: int = Field(0, description="Oportunidades buenas")
    average: int = Field(0, description="Oportunidades medias")
    poor: int = Field(0, description="Oportunidades bajas")
    rejected: int = Field(0, description="Rechazados")


class SearchResultItem(BaseModel):
    """Resultado individual de búsqueda con análisis completo."""

    # Información básica del vehículo
    source: str | None = Field(None, description="Proveedor de origen")
    external_id: str | None = Field(None, description="ID externo en el proveedor")
    url: str | None = Field(None, description="URL del anuncio")
    brand: str | None = Field(None, description="Marca")
    model: str | None = Field(None, description="Modelo")
    year: int | None = Field(None, description="Año de fabricación")
    mileage: int | None = Field(None, description="Kilometraje")
    fuel_type: str | None = Field(None, description="Tipo de combustible")
    transmission: str | None = Field(None, description="Tipo de transmisión")
    power_hp: int | None = Field(None, description="Potencia (HP)")
    price: float | None = Field(None, description="Precio de venta (EUR)")
    currency: str | None = Field(None, description="Moneda")
    location: str | None = Field(None, description="Ubicación")
    images: list[str] = Field(default_factory=list, description="URLs de imágenes")
    description: str | None = Field(None, description="Descripción del anuncio")

    # Análisis completo
    vehicle_score: VehicleScoreSchema | None = Field(
        None, description="Puntuación del vehículo"
    )
    market_estimation: MarketEstimationSchema | None = Field(
        None, description="Estimación de mercado"
    )
    profit_analysis: ProfitAnalysisSchema | None = Field(
        None, description="Análisis de rentabilidad"
    )
    opportunity: OpportunityAnalysisSchema | None = Field(
        None, description="Análisis de oportunidad"
    )
    recommendation_label_es: str = Field(
        default="",
        description="Etiqueta legible en español de la recomendación (REC.1)",
    )
    risk_label_es: str = Field(
        default="",
        description="Etiqueta legible en español del nivel de riesgo (REC.1)",
    )
    negotiation: NegotiationResultSchema | None = Field(
        None, description="Estrategia de negociación"
    )


class ProviderIssueSchema(BaseModel):
    """Provider que falló durante la búsqueda (SEARCH.DIAG.1)."""

    provider: str = Field(..., description="Nombre del provider")
    stage: str = Field(
        ..., description="Dónde falló: registry | search | analyze"
    )
    error_type: str = Field(..., description="Clase de la excepción")
    message: str = Field(..., description="Mensaje del error")
    message_es: str = Field(..., description="Mensaje para mostrar al usuario")
    external_id: str | None = Field(
        None, description="Vehículo afectado (solo en stage=analyze)"
    )


class SearchAPIResponse(BaseModel):
    """Respuesta completa de una búsqueda."""

    summary: SearchSummarySchema = Field(..., description="Resumen de resultados")
    results: list[SearchResultItem] = Field(
        ..., description="Lista de resultados analizados"
    )
    provider_issues: list[ProviderIssueSchema] = Field(
        default_factory=list,
        description=(
            "Providers que fallaron. Vacío = todos respondieron. Permite "
            "distinguir 'no hay coches' de 'la fuente se cayó'."
        ),
    )

