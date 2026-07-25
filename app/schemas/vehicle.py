from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class VehicleBase(BaseModel):
    source: str = Field(..., max_length=50)
    external_id: str = Field(..., max_length=255)
    url: str | None = None
    brand: str = Field(..., max_length=100)
    model: str = Field(..., max_length=100)
    version: str | None = Field(default=None, max_length=255)
    year: int | None = None
    mileage: int | None = None
    fuel_type: str | None = Field(default=None, max_length=50)
    transmission: str | None = Field(default=None, max_length=50)
    power_hp: int | None = None
    displacement_cc: int | None = None
    doors: int | None = None
    color: str | None = Field(default=None, max_length=50)
    emissions: str | None = Field(default=None, max_length=50)
    location: str | None = Field(default=None, max_length=255)
    seller_type: str | None = Field(default=None, max_length=50)
    first_registration: str | None = Field(default=None, max_length=50)
    price: float | None = None
    currency: str | None = Field(default=None, max_length=10)
    vin: str | None = Field(default=None, max_length=50)
    description: str | None = None
    images: str | None = None
    equipment: str | None = None


class VehicleCreate(VehicleBase):
    pass


class VehicleRead(VehicleBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    updated_at: datetime


class VehicleUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: str | None = None
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
    images: str | None = None
    equipment: str | None = None