from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AuditLog(Base):
    """Immutable audit log entry - create and read only."""

    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_resource_id", "resource_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    # TASK 9 (AUD-018): FK real a users.id. SET NULL (no CASCADE): borrar un
    # usuario no debe borrar su historial de auditoría, solo desvincularlo.
    user_id: Mapped[str | None] = mapped_column(
        Uuid(as_uuid=False),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    action: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    resource: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    # resource_id es deliberadamente polimórfico (vehicle/opportunity/deal/...
    # según `resource`): no lleva FK porque no apunta a una única tabla.
    resource_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    def __init__(self, **kwargs: object) -> None:
        super().__init__(**kwargs)
        if getattr(self, "id", None) is None:
            self.id = str(uuid4())
        if getattr(self, "timestamp", None) is None:
            self.timestamp = datetime.now(UTC)
