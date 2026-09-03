"""Pydantic schemas for feature flags — TASK-012."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class FeatureFlagRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    key: str
    value: bool
    description: str | None
    created_at: datetime
    updated_at: datetime


class FeatureFlagCreate(BaseModel):
    key: str = Field(..., min_length=1, max_length=100)
    value: bool = False
    description: str | None = None


class FeatureFlagUpdate(BaseModel):
    value: bool
    description: str | None = None