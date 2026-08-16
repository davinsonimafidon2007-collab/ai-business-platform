"""Vehicle detail and provider list endpoint schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.api.v1.schemas.common import CostLineSchema


class VehicleDetailResponse(BaseModel):
    """Información detallada de un vehículo desde un provider."""

    source: str = Field(..., description="Proveedor de origen")
    external_id: str = Field(..., description="ID externo en el proveedor")
    url: str | None = Field(None, description="URL del anuncio")
    brand: str | None = Field(None, description="Marca")
    model: str | None = Field(None, description="Modelo")
    category: str | None = Field(None, description="Categoría")
    version: str | None = Field(None, description="Versión")
    year: int | None = Field(None, description="Año de fabricación")
    mileage: int | None = Field(None, description="Kilometraje")
    fuel_type: str | None = Field(None, description="Tipo de combustible")
    transmission: str | None = Field(None, description="Tipo de transmisión")
    power_hp: int | None = Field(None, description="Potencia (HP)")
    displacement_cc: int | None = Field(None, description="Cilindrada (cc)")
    doors: int | None = Field(None, description="Número de puertas")
    color: str | None = Field(None, description="Color")
    emissions: str | None = Field(None, description="Emisiones")
    location: str | None = Field(None, description="Ubicación")
    seller_type: str | None = Field(None, description="Tipo de vendedor")
    first_registration: str | None = Field(None, description="Primera matriculación")
    price: float | None = Field(None, description="Precio (EUR)")
    currency: str | None = Field(None, description="Moneda")
    vin: str | None = Field(None, description="Número de bastidor (VIN)")
    description: str | None = Field(None, description="Descripción")
    images: list[str] = Field(default_factory=list, description="URLs de imágenes")
    equipment: list[str] = Field(default_factory=list, description="Equipamiento")


class ProviderListResponse(BaseModel):
    """Lista de proveedores disponibles."""

    providers: list[str] = Field(
        ..., description="Nombres de los proveedores registrados"
    )


class SimulateProfitRequest(BaseModel):
    """Petición de simulación de beneficio what-if sobre un vehículo."""

    profile_name: str = Field(
        default="SPAIN", description="Perfil de costes (ES, SPAIN, PT, ...)"
    )
    purchase_price: float | None = Field(
        default=None,
        description="Override del precio de compra; si null usa vehicle.price",
    )
    estimated_sale_price: float | None = Field(
        default=None,
        description="Precio de venta estimado en destino; si null el analyzer usa su default",
    )


class SimulateProfitResponse(BaseModel):
    """Resultado de la simulación de beneficio what-if."""

    profile_name: str
    purchase_price: float
    estimated_sale_price: float | None
    total_cost: float
    net_profit: float
    roi_percentage: float
    recommendation: str
    risk_level: str
    transport_cost: float
    registration_cost: float
    taxes: float
    inspection_cost: float
    commission_cost: float
    repair_estimate: float
    miscellaneous_cost: float
    # --- SIM.1 ---
    cost_lines: list[CostLineSchema] = Field(default_factory=list)
    coherence_warnings: list[str] = Field(default_factory=list)
    recommendation_label_es: str = Field(
        default="",
        description="Etiqueta legible en español de la recomendación (REC.1)",
    )
    risk_label_es: str = Field(
        default="",
        description="Etiqueta legible en español del nivel de riesgo (REC.1)",
    )

