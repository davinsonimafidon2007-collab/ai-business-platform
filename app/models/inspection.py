"""Modelos de datos para el módulo Inspection Session.

Solo se persisten en base de datos:
    - InspectionSession (cabecera de la sesión)
    - InspectionObservation (observación de un punto concreto)
    - InspectionPhoto (fotografía asociada a una observación)

Las categorías y puntos de inspección provienen del catálogo estático
en app/config/inspection.py, no de la base de datos.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config.inspection import (
    InspectionItemStatus,
    InspectionSessionStatus,
    SeverityLevel,
)
from app.models.base import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.vehicle import Vehicle


class InspectionSession(Base):
    """Sesión de inspección de un vehículo.

    Almacena el estado global de la inspección.
    Las categorías e ítems se cargan desde el catálogo estático.
    Las observaciones se almacenan en InspectionObservation.
    """

    __tablename__ = "inspection_sessions"
    __table_args__ = (
        Index("ix_inspection_sessions_vehicle_id", "vehicle_id"),
        Index("ix_inspection_sessions_user_id", "user_id"),
        Index("ix_inspection_sessions_created_at", "created_at"),
    )

    id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    # TASK 9 (AUD-017): índices en las FKs más consultadas (antes ninguna
    # tabla de inspección tenía índice: InspectionObservationRepository.
    # get_by_session, InspectionPhotoRepository.get_by_session/
    # get_by_observation escaneaban la tabla entera). Declarados en
    # __table_args__ arriba (no también como index=True por columna: crear
    # el mismo índice dos veces con el mismo nombre auto-generado rompe
    # create_all en SQLite).
    vehicle_id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False),
        ForeignKey("vehicles.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default=InspectionSessionStatus.DRAFT.value,
        nullable=False,
    )
    current_category_order: Mapped[int] = mapped_column(
        Integer, default=1, nullable=False
    )
    """Orden de la categoría actual (para reanudar el flujo)."""

    total_repair_cost: Mapped[float] = mapped_column(
        Float, default=0.0, nullable=False
    )
    total_defects: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_critical_defects: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    risk_level: Mapped[str | None] = mapped_column(
        String(20), nullable=True, default=None
    )
    recommendation: Mapped[str | None] = mapped_column(
        Text, nullable=True, default=None
    )
    overall_condition: Mapped[int | None] = mapped_column(
        Integer, nullable=True, default=None
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )

    # Storage for summary JSON (generado al finalizar)
    _summary_json: Mapped[str | None] = mapped_column(
        "summary_json", Text, nullable=True, default=None
    )

    vehicle: Mapped[Vehicle] = relationship("Vehicle", back_populates="inspection_sessions")
    user: Mapped[User] = relationship("User", back_populates="inspection_sessions")
    observations: Mapped[list[InspectionObservation]] = relationship(
        "InspectionObservation",
        back_populates="session",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    photos: Mapped[list[InspectionPhoto]] = relationship(
        "InspectionPhoto",
        back_populates="session",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __init__(self, **kwargs: Any) -> None:
        """Inicializa la sesión con valores por defecto."""
        summary = kwargs.pop("summary", None)
        super().__init__(**kwargs)
        if getattr(self, "status", None) is None:
            self.status = InspectionSessionStatus.DRAFT.value
        if getattr(self, "current_category_order", None) is None:
            self.current_category_order = 1
        if getattr(self, "total_repair_cost", None) is None:
            self.total_repair_cost = 0.0
        if getattr(self, "total_defects", None) is None:
            self.total_defects = 0
        if getattr(self, "total_critical_defects", None) is None:
            self.total_critical_defects = 0
        if getattr(self, "id", None) is None:
            self.id = str(uuid4())
        now = datetime.now(UTC)
        if getattr(self, "created_at", None) is None:
            self.created_at = now
        if getattr(self, "updated_at", None) is None:
            self.updated_at = now
        if summary is not None:
            self.summary = summary

    @property
    def summary(self) -> dict[str, Any] | None:
        """Deserializa el summary JSON."""
        if self._summary_json is None:
            return None
        try:
            return json.loads(self._summary_json)
        except (json.JSONDecodeError, TypeError):
            return None

    @summary.setter
    def summary(self, value: dict[str, Any] | None) -> None:
        """Serializa summary a JSON string."""
        if value is None:
            self._summary_json = None
        else:
            self._summary_json = json.dumps(value, ensure_ascii=False, default=str)

    def to_dict(self) -> dict[str, Any]:
        """Convierte la sesión a dict para serialización."""
        return {
            "id": self.id,
            "vehicle_id": self.vehicle_id,
            "user_id": self.user_id,
            "status": self.status,
            "current_category_order": self.current_category_order,
            "total_repair_cost": self.total_repair_cost,
            "total_defects": self.total_defects,
            "total_critical_defects": self.total_critical_defects,
            "risk_level": self.risk_level,
            "recommendation": self.recommendation,
            "overall_condition": self.overall_condition,
            "notes": self.notes,
            "summary": self.summary,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class InspectionObservation(Base):
    """Observación de un punto de inspección concreto.

    Cada fila representa la revisión de un ítem del catálogo
    durante una sesión de inspección.
    """

    __tablename__ = "inspection_observations"
    __table_args__ = (
        Index("ix_inspection_observations_session_id", "session_id"),
        Index("ix_inspection_observations_category_item", "session_id", "category_id", "item_id", unique=True),
    )

    id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    session_id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False),
        ForeignKey("inspection_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    category_id: Mapped[str] = mapped_column(String(50), nullable=False)
    """ID de la categoría (ej: 'exterior'). Ref al catálogo estático."""
    item_id: Mapped[str] = mapped_column(String(50), nullable=False)
    """ID del ítem (ej: 'pintura'). Ref al catálogo estático."""

    status: Mapped[str] = mapped_column(
        String(20),
        default=InspectionItemStatus.UNKNOWN.value,
        nullable=False,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    estimated_repair_cost: Mapped[float | None] = mapped_column(
        Float, nullable=True, default=None
    )
    severity: Mapped[str] = mapped_column(
        String(20),
        default=SeverityLevel.LOW.value,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    session: Mapped[InspectionSession] = relationship("InspectionSession", back_populates="observations")
    photos: Mapped[list[InspectionPhoto]] = relationship(
        "InspectionPhoto",
        back_populates="observation",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __init__(self, **kwargs: Any) -> None:
        """Inicializa la observación con valores por defecto."""
        super().__init__(**kwargs)
        if getattr(self, "status", None) is None:
            self.status = InspectionItemStatus.UNKNOWN.value
        if getattr(self, "severity", None) is None:
            self.severity = SeverityLevel.LOW.value
        if getattr(self, "id", None) is None:
            self.id = str(uuid4())
        now = datetime.now(UTC)
        if getattr(self, "created_at", None) is None:
            self.created_at = now
        if getattr(self, "updated_at", None) is None:
            self.updated_at = now

    def to_dict(self) -> dict[str, Any]:
        """Convierte la observación a dict para serialización."""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "category_id": self.category_id,
            "item_id": self.item_id,
            "status": self.status,
            "notes": self.notes,
            "estimated_repair_cost": self.estimated_repair_cost,
            "severity": self.severity,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class InspectionPhoto(Base):
    """Fotografía asociada a una observación de inspección.

    Almacena la referencia al archivo, no el binario.
    Preparado para que un VisionProvider analice la imagen en el futuro.
    """

    __tablename__ = "inspection_photos"
    __table_args__ = (
        Index("ix_inspection_photos_observation_id", "observation_id"),
        Index("ix_inspection_photos_session_id", "session_id"),
    )

    id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    observation_id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False),
        ForeignKey("inspection_observations.id", ondelete="CASCADE"),
        nullable=False,
    )
    session_id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False),
        ForeignKey("inspection_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Almacenamos la URL/ruta del archivo
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    """Ruta o URL donde está almacenada la fotografía."""
    file_name: Mapped[str | None] = mapped_column(
        String(255), nullable=True, default=None
    )
    """Nombre original del archivo."""
    mime_type: Mapped[str | None] = mapped_column(
        String(100), nullable=True, default=None
    )
    """Tipo MIME (image/jpeg, image/png, ...)."""
    file_size_bytes: Mapped[int | None] = mapped_column(
        Integer, nullable=True, default=None
    )

    # Preparado para análisis futuro con IA
    ai_analysis_status: Mapped[str] = mapped_column(
        String(20), default="PENDING", nullable=False
    )
    """Estado del análisis por IA: PENDING, PROCESSING, COMPLETED, FAILED."""
    ai_analysis_result: Mapped[str | None] = mapped_column(
        Text, nullable=True, default=None
    )
    """Resultado del análisis en JSON string (cuando se implemente IA)."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
    )

    observation: Mapped[InspectionObservation] = relationship("InspectionObservation", back_populates="photos")
    session: Mapped[InspectionSession] = relationship("InspectionSession", back_populates="photos")

    def __init__(self, **kwargs: Any) -> None:
        """Inicializa la foto con valores por defecto."""
        super().__init__(**kwargs)
        if getattr(self, "ai_analysis_status", None) is None:
            self.ai_analysis_status = "PENDING"
        if getattr(self, "id", None) is None:
            self.id = str(uuid4())
        if getattr(self, "created_at", None) is None:
            self.created_at = datetime.now(UTC)

    def to_dict(self) -> dict[str, Any]:
        """Convierte la foto a dict para serialización."""
        return {
            "id": self.id,
            "observation_id": self.observation_id,
            "session_id": self.session_id,
            "file_path": self.file_path,
            "file_name": self.file_name,
            "mime_type": self.mime_type,
            "file_size_bytes": self.file_size_bytes,
            "ai_analysis_status": self.ai_analysis_status,
            "ai_analysis_result": self.ai_analysis_result,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
