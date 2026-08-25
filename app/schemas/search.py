from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


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
    user_id: str
    created_at: datetime
    # Compat: API exposes `timestamp` alias for created_at
    timestamp: datetime | None = Field(default=None)

    def model_post_init(self, __context: object) -> None:
        if self.timestamp is None and getattr(self, "created_at", None) is not None:
            object.__setattr__(self, "timestamp", self.created_at)


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