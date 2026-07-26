from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class VehicleSearchResult:
    """DTO que representa un resultado de búsqueda devuelto por un provider.

    Es el formato interno de la capa de providers, independiente de los
    modelos SQLAlchemy y de los schemas Pydantic de la API.
    """
    source: str
    external_id: str
    url: str | None = None
    brand: str | None = None
    model: str | None = None
    category: str | None = None
    version: str | None = None
    year: int | None = None
    mileage: int | None = None
    fuel_type: str | None = None
    transmission: str | None = None
    power_hp: int | None = None
    displacement_cc: int | None = None
    doors: int | None = None
    color: str | None = None
    emissions: str | None = None
    location: str | None = None
    seller_type: str | None = None
    first_registration: str | None = None
    price: float | None = None
    currency: str | None = None
    vin: str | None = None
    description: str | None = None
    images: list[str] = field(default_factory=list)
    equipment: list[str] = field(default_factory=list)
    raw_data: dict[str, Any] = field(default_factory=dict)


@dataclass
class VehicleDetail:
    """DTO que representa la información detallada de un vehículo.

    Se obtiene al consultar un vehículo concreto por su ID en el provider.
    """
    source: str
    external_id: str
    url: str | None = None
    brand: str | None = None
    model: str | None = None
    category: str | None = None
    version: str | None = None
    year: int | None = None
    mileage: int | None = None
    fuel_type: str | None = None
    transmission: str | None = None
    power_hp: int | None = None
    displacement_cc: int | None = None
    doors: int | None = None
    color: str | None = None
    emissions: str | None = None
    location: str | None = None
    seller_type: str | None = None
    first_registration: str | None = None
    price: float | None = None
    currency: str | None = None
    vin: str | None = None
    description: str | None = None
    images: list[str] = field(default_factory=list)
    equipment: list[str] = field(default_factory=list)
    raw_data: dict[str, Any] = field(default_factory=dict)
