"""Repositorio para el módulo Inspection Session.

Gestiona la persistencia de InspectionSession, InspectionObservation
e InspectionPhoto en base de datos.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import and_, delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.inspection import InspectionObservation, InspectionPhoto, InspectionSession


class InspectionSessionRepository:
    """Repositorio para InspectionSession."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, inspection: InspectionSession) -> InspectionSession:
        """Crea una nueva sesión de inspección."""
        self.session.add(inspection)
        await self.session.commit()
        await self.session.refresh(inspection)
        return inspection

    async def get_by_id(self, inspection_id: str | UUID) -> InspectionSession | None:
        """Obtiene una sesión por su ID."""
        result = await self.session.execute(
            select(InspectionSession).where(InspectionSession.id == str(inspection_id))
        )
        return result.scalar_one_or_none()

    async def get_by_vehicle_id(
        self, vehicle_id: str | UUID
    ) -> list[InspectionSession]:
        """Obtiene todas las sesiones de un vehículo."""
        result = await self.session.execute(
            select(InspectionSession)
            .where(InspectionSession.vehicle_id == str(vehicle_id))
            .order_by(InspectionSession.created_at.desc())
        )
        return list(result.scalars().all())

    async def list_all(
        self, skip: int = 0, limit: int = 100
    ) -> list[InspectionSession]:
        """Lista todas las sesiones."""
        result = await self.session.execute(
            select(InspectionSession)
            .offset(skip)
            .limit(limit)
            .order_by(InspectionSession.created_at.desc())
        )
        return list(result.scalars().all())

    async def update(self, inspection: InspectionSession) -> InspectionSession:
        """Actualiza una sesión existente."""
        await self.session.commit()
        await self.session.refresh(inspection)
        return inspection

    async def delete(self, inspection: InspectionSession) -> None:
        """Elimina una sesión."""
        await self.session.delete(inspection)
        await self.session.commit()

class InspectionObservationRepository:
    """Repositorio para InspectionObservation."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self, observation: InspectionObservation
    ) -> InspectionObservation:
        """Crea una nueva observación."""
        self.session.add(observation)
        await self.session.commit()
        await self.session.refresh(observation)
        return observation

    async def get_by_id(
        self, observation_id: str | UUID
    ) -> InspectionObservation | None:
        """Obtiene una observación por su ID."""
        result = await self.session.execute(
            select(InspectionObservation).where(
                InspectionObservation.id == str(observation_id)
            )
        )
        return result.scalar_one_or_none()

    async def get_by_session(
        self, session_id: str | UUID
    ) -> list[InspectionObservation]:
        """Obtiene todas las observaciones de una sesión."""
        result = await self.session.execute(
            select(InspectionObservation)
            .where(InspectionObservation.session_id == str(session_id))
            .order_by(InspectionObservation.category_id, InspectionObservation.item_id)
        )
        return list(result.scalars().all())

    async def get_by_category(
        self, session_id: str | UUID, category_id: str
    ) -> list[InspectionObservation]:
        """Obtiene las observaciones de una categoría en una sesión."""
        result = await self.session.execute(
            select(InspectionObservation).where(
                and_(
                    InspectionObservation.session_id == str(session_id),
                    InspectionObservation.category_id == category_id,
                )
            )
        )
        return list(result.scalars().all())

    async def get_by_item(
        self, session_id: str | UUID, category_id: str, item_id: str
    ) -> InspectionObservation | None:
        """Obtiene la observación de un ítem concreto."""
        result = await self.session.execute(
            select(InspectionObservation).where(
                and_(
                    InspectionObservation.session_id == str(session_id),
                    InspectionObservation.category_id == category_id,
                    InspectionObservation.item_id == item_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def update(
        self, observation: InspectionObservation
    ) -> InspectionObservation:
        """Actualiza una observación existente."""
        await self.session.commit()
        await self.session.refresh(observation)
        return observation

    async def delete(self, observation: InspectionObservation) -> None:
        """Elimina una observación."""
        await self.session.delete(observation)
        await self.session.commit()

    async def delete_by_session(self, session_id: str | UUID) -> None:
        """Elimina todas las observaciones de una sesión."""
        await self.session.execute(
            delete(InspectionObservation).where(
                InspectionObservation.session_id == str(session_id)
            )
        )
        await self.session.commit()


class InspectionPhotoRepository:
    """Repositorio para InspectionPhoto."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, photo: InspectionPhoto) -> InspectionPhoto:
        """Crea una nueva foto."""
        self.session.add(photo)
        await self.session.commit()
        await self.session.refresh(photo)
        return photo

    async def get_by_id(self, photo_id: str | UUID) -> InspectionPhoto | None:
        """Obtiene una foto por su ID."""
        result = await self.session.execute(
            select(InspectionPhoto).where(InspectionPhoto.id == str(photo_id))
        )
        return result.scalar_one_or_none()

    async def get_by_observation(
        self, observation_id: str | UUID
    ) -> list[InspectionPhoto]:
        """Obtiene todas las fotos de una observación."""
        result = await self.session.execute(
            select(InspectionPhoto).where(
                InspectionPhoto.observation_id == str(observation_id)
            )
        )
        return list(result.scalars().all())

    async def get_by_session(
        self, session_id: str | UUID
    ) -> list[InspectionPhoto]:
        """Obtiene todas las fotos de una sesión."""
        result = await self.session.execute(
            select(InspectionPhoto).where(
                InspectionPhoto.session_id == str(session_id)
            )
        )
        return list(result.scalars().all())

    async def delete(self, photo: InspectionPhoto) -> None:
        """Elimina una foto."""
        await self.session.delete(photo)
        await self.session.commit()

    async def delete_by_session(self, session_id: str | UUID) -> None:
        """Elimina todas las fotos de una sesión."""
        await self.session.execute(
            delete(InspectionPhoto).where(
                InspectionPhoto.session_id == str(session_id)
            )
        )
        await self.session.commit()

