"""Pydantic schemas for API key management (Task F.2)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ApiKeyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    scopes: str | None = Field(default=None, max_length=500)
    expires_at: datetime | None = None


class ApiKeyRead(BaseModel):
    """Metadata pública. Nunca incluye raw key ni key_hash."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    prefix: str
    scopes: str | None = None
    description: str | None = None
    expires_at: datetime | None = None
    is_active: bool
    last_used_at: datetime | None = None
    created_at: datetime


class ApiKeyCreated(ApiKeyRead):
    """Respuesta de POST: incluye la key completa una sola vez."""

    api_key: str = Field(..., description="Full API key. Shown only once.")


class ApiKeyListResponse(BaseModel):
    items: list[ApiKeyRead]
    total: int
