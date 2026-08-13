from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

# Re-exporting API v1 schemas for unification (TASK-014)
from app.api.v1.schemas.search import (
    ProviderIssueSchema as ProviderIssueSchema,  # noqa: F401
)
from app.api.v1.schemas.search import (
    SearchAPIRequest as SearchAPIRequest,  # noqa: F401
)
from app.api.v1.schemas.search import (
    SearchAPIResponse as SearchAPIResponse,  # noqa: F401
)
from app.api.v1.schemas.search import (
    SearchResultItem as SearchResultItem,  # noqa: F401
)
from app.api.v1.schemas.search import (
    SearchSummarySchema as SearchSummarySchema,  # noqa: F401
)


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