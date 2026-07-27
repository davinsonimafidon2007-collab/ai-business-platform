"""Vehicle detail and provider list endpoint schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


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

