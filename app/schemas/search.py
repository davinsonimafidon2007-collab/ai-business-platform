from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.search import ProviderIssue

__all__ = [
    "ProviderIssue",
    "SearchBase",
    "SearchCreate",
    "SearchRead",
    "SearchUpdate",
]


class SearchBase(BaseModel):
    name: str = Field(..., max_length=255)
    country: str = Field(..., max_length=10)
    brands: str | None = None
    models: str | None = None
    filters: str | None = None
    query: str | None = Field(default=None, max_length=500)
    results_count: int | None = None
    execution_time: float | None = None


class SearchCreate(SearchBase):
    pass


class SearchRead(SearchBase):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str
    timestamp: datetime = Field(validation_alias="created_at", serialization_alias="timestamp")


class SearchUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, max_length=255)
    country: str | None = Field(default=None, max_length=10)
    brands: str | None = None
    models: str | None = None
    filters: str | None = None
    query: str | None = Field(default=None, max_length=500)
    results_count: int | None = None
    execution_time: float | None = None