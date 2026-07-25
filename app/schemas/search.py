from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SearchBase(BaseModel):
    name: str = Field(..., max_length=255)
    country: str = Field(..., max_length=10)
    brands: str | None = None
    models: str | None = None
    filters: str | None = None


class SearchCreate(SearchBase):
    pass


class SearchRead(SearchBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime


class SearchUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, max_length=255)
    country: str | None = Field(default=None, max_length=10)
    brands: str | None = None
    models: str | None = None
    filters: str | None = None