"""Servicio de gestión de deals (pipeline de ventas) — Task D.1.

Valida las transiciones de estado del pipeline:

    NEW       -> CONTACTED, DROPPED
    CONTACTED -> OFFER, LOST, DROPPED
    OFFER     -> WON, LOST, DROPPED
    WON / LOST / DROPPED -> terminal (sin salida)

La propiedad de cada deal se restringe a su ``user_id``: cualquier intento
de acceder o transicionar un deal ajeno se trata como 404 (no se filtra la
existencia de recursos ajenos).
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException, status

from app.models.deal import Deal, DealStatus
from app.repositories.deal_repository import DealRepository


class DealService:
    """Servicio de dominio para el pipeline de deals."""

    # Transiciones válidas por estado actual.
    _TRANSITIONS: dict[DealStatus, set[DealStatus]] = {
        DealStatus.NEW: {DealStatus.CONTACTED, DealStatus.DROPPED},
        DealStatus.CONTACTED: {
            DealStatus.OFFER,
            DealStatus.LOST,
            DealStatus.DROPPED,
        },
        DealStatus.OFFER: {DealStatus.WON, DealStatus.LOST, DealStatus.DROPPED},
        # Terminales: WON, LOST, DROPPED no tienen salida
        DealStatus.WON: set(),
        DealStatus.LOST: set(),
        DealStatus.DROPPED: set(),
    }

    def __init__(self, repository: DealRepository) -> None:
        self.repository = repository

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    async def create(
        self,
        *,
        user_id: str,
        opportunity_id: str | None = None,
        vehicle_id: str | None = None,
        notes: str | None = None,
        contact_channel: str | None = None,
    ) -> Deal:
        """Crea un nuevo deal en estado NEW.

        Exige al menos un vínculo (opportunity_id o vehicle_id). Si se
        proporciona ``opportunity_id`` y ya existe un deal activo
        (NEW|CONTACTED|OFFER) para el mismo usuario y oportunidad, se
        rechaza con 409 para evitar duplicados activos.

        Args:
            user_id: Dueño del deal.
            opportunity_id: Oportunidad de origen (opcional).
            vehicle_id: Vehículo asociado (opcional).
            notes: Notas iniciales (opcional).
            contact_channel: Canal de contacto (opcional).

        Returns:
            El Deal creado con estado NEW.

        Raises:
            HTTPException 422: Si no se proporciona ni opportunity ni vehicle.
            HTTPException 409: Si ya existe un deal activo para la oportunidad.
        """
        if not opportunity_id and not vehicle_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="At least one of opportunity_id or vehicle_id is required",
            )

        # Un solo deal activo por opportunity/user. Si ya existe un deal en
        # estado NEW|CONTACTED|OFFER, se rechaza (409) para evitar duplicados.
        if opportunity_id:
            existing = await self.repository.get_active_by_opportunity(
                user_id, opportunity_id
            )
            if existing is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "message": (
                            "You already have an active deal for this opportunity"
                        ),
                        "deal_id": existing.id,
                    },
                )

        deal = Deal(
            user_id=user_id,
            opportunity_id=opportunity_id,
            vehicle_id=vehicle_id,
            status=DealStatus.NEW,
            notes=notes,
            contact_channel=contact_channel,
        )
        return await self.repository.create(deal)

    async def list(
        self,
        *,
        user_id: str,
        deal_status: DealStatus | str | None = None,
        opportunity_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Deal], int]:
        """Lista deals del usuario (solo los suyos), con filtros opcionales."""
        return await self.repository.list_for_user(
            user_id=user_id,
            status=deal_status,
            opportunity_id=opportunity_id,
            limit=limit,
            offset=offset,
        )

    async def get(self, deal_id: str, user_id: str) -> Deal:
        """Obtiene un deal comprobando ownership.

        Raises:
            HTTPException 404: Si el deal no existe o no pertenece al usuario.
        """
        deal = await self.repository.get_by_id(deal_id)
        if deal is None or deal.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Deal not found",
            )
        return deal

    async def transition(
        self,
        *,
        deal_id: str,
        user_id: str,
        new_status: DealStatus,
        notes: str | None = None,
        offer_price: float | None = None,
    ) -> Deal:
        """Transiciona un deal a un nuevo estado, validando la transición.

        Args:
            deal_id: Id del deal a transicionar.
            user_id: Dueño del deal (ownership check).
            new_status: Estado destino.
            notes: Notas opcionales a añadir/actualizar.
            offer_price: Precio de oferta opcional (p.ej. en OFFER/WON).

        Returns:
            El Deal actualizado.

        Raises:
            HTTPException 404: Si el deal no existe o no pertenece al usuario.
            HTTPException 422: Si la transición no es válida.
        """
        deal = await self.get(deal_id, user_id)

        allowed = self._TRANSITIONS.get(deal.status, set())
        if new_status not in allowed:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"Invalid transition from {deal.status.value} "
                    f"to {new_status.value}"
                ),
            )

        deal.status = new_status
        if notes is not None:
            deal.notes = notes
        if offer_price is not None:
            deal.offer_price = offer_price
        deal.updated_at = self._now()

        return await self.repository.update(deal)

    async def save_simulation(
        self,
        *,
        deal_id: str,
        user_id: str,
        purchase_price: float | None = None,
        estimated_sale_price: float | None = None,
        total_cost: float | None = None,
        net_profit: float | None = None,
        roi_percentage: float | None = None,
        profile_name: str | None = None,
    ) -> Deal:
        """Guarda la última simulación de margen en un deal (Task E.2).

        Solo actualiza los campos de simulación ``last_sim_*`` y el timestamp
        ``last_sim_at`` / ``updated_at``. No modifica el estado del pipeline ni
        los campos de negociación (offer_price, notes, contact_channel).

        Args:
            deal_id: Id del deal en el que guardar la simulación.
            user_id: Dueño del deal (ownership check).
            purchase_price: Precio de compra de la simulación.
            estimated_sale_price: Precio de venta estimado.
            total_cost: Coste total de la simulación.
            net_profit: Beneficio neto de la simulación.
            roi_percentage: ROI (%) de la simulación.
            profile_name: Perfil de costes usado.

        Returns:
            El Deal actualizado con los campos de simulación.

        Raises:
            HTTPException 404: Si el deal no existe o no pertenece al usuario.
        """
        deal = await self.get(deal_id, user_id)

        now = self._now()
        deal.last_sim_purchase_price = purchase_price
        deal.last_sim_sale_price = estimated_sale_price
        deal.last_sim_total_cost = total_cost
        deal.last_sim_net_profit = net_profit
        deal.last_sim_roi = roi_percentage
        deal.last_sim_profile = profile_name
        deal.last_sim_at = now
        deal.updated_at = now

        return await self.repository.update(deal)
