from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Enum, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.role import Role

if TYPE_CHECKING:
    from app.models.api_key import ApiKey
    from app.models.deal import Deal
    from app.models.inspection import InspectionSession
    from app.models.refresh_token import RefreshToken
    from app.models.search import Search
    from app.models.search_history import SearchHistory
    from app.models.search_order import SearchOrder
    from app.models.vehicle import Vehicle


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    role: Mapped[Role] = mapped_column(
        Enum(Role, name="role", values_callable=lambda roles: [role.value for role in roles]),
        default=Role.USER,
        server_default=Role.USER.value,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    vehicles: Mapped[list[Vehicle]] = relationship(
        "Vehicle",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    searches: Mapped[list[Search]] = relationship(
        "Search",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    deals: Mapped[list[Deal]] = relationship(
        "Deal",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    api_keys: Mapped[list[ApiKey]] = relationship(
        "ApiKey",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    refresh_tokens: Mapped[list[RefreshToken]] = relationship(
        "RefreshToken",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    search_histories: Mapped[list[SearchHistory]] = relationship(
        "SearchHistory",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    search_orders: Mapped[list[SearchOrder]] = relationship(
        "SearchOrder",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    inspection_sessions: Mapped[list[InspectionSession]] = relationship(
        "InspectionSession",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __init__(self, **kwargs: object) -> None:
        super().__init__(**kwargs)
        if getattr(self, "id", None) is None:
            self.id = str(uuid4())
        if getattr(self, "is_active", None) is None:
            self.is_active = True
        if getattr(self, "is_verified", None) is None:
            self.is_verified = False
        if getattr(self, "role", None) is None:
            self.role = Role.USER
        if getattr(self, "created_at", None) is None:
            self.created_at = datetime.now(UTC)
        if getattr(self, "updated_at", None) is None:
            self.updated_at = datetime.now(UTC)
