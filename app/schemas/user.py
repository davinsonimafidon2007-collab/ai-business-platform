from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = Field(default=None, max_length=255)
    is_active: bool = True


class UserCreate(UserBase):
    hashed_password: str = Field(..., min_length=1, max_length=255)


class UserRead(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime


class UserUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr | None = None
    full_name: Optional[str] = Field(default=None, max_length=255)
    is_active: bool | None = None
    hashed_password: str | None = Field(default=None, min_length=1, max_length=255)
