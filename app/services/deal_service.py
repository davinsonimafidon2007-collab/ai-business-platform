"""Servicio de gestión de deals (pipeline de ventas) — Task D.1, extendido TASK 3.

Valida las transiciones de estado del pipeline:

    NEW       -> CONTACTED, DROPPED
    CONTACTED -> OFFER, LOST, DROPPED
    OFFER     -> WON, LOST, DROPPED
    WON       -> BOUGHT, DROPPED
    BOUGHT    -> IN_TRANSIT, DROPPED
    IN_TRANSIT -> REGISTERED, DROPPED
    REGISTERED -> SOLD, DROPPED
    SOLD / LOST / DROPPED -> terminal (sin salida)

LOST solo es alcanzable antes de WON (fallo de negociación); tras comprar
el vehículo, un trato que no llega a buen fin es DROPPED.

La propiedad de cada deal se restringe a su ``user_id``: cualquier intento
de acceder o transicionar un deal ajeno se trata como 404 (no se filtra la
existencia de recursos ajenos).
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import HTTPException, status

from app.models.deal import Deal, DealStatus
from app.repositories.deal_repository import DealRepository
from app.repositories.vehicle_evaluation_repository import VehicleEvaluationRepository


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
        DealStatus.WON: {DealStatus.BOUGHT, DealStatus.DROPPED},
        DealStatus.BOUGHT: {DealStatus.IN_TRANSIT, DealStatus.DROPPED},
        DealStatus.IN_TRANSIT: {DealStatus.REGISTERED, DealStatus.DROPPED},
        DealStatus.REGISTERED: {DealStatus.SOLD, DealStatus.DROPPED},
        # Terminales: SOLD, LOST, DROPPED no tienen salida
        DealStatus.SOLD: set(),
        DealStatus.LOST: set(),
        DealStatus.DROPPED: set(),
    }

    def __init__(
        self,
        repository: DealRepository,
        evaluation_repository: VehicleEvaluationRepository | None = None,
    ) -> None:
        self.repository = repository
        self.evaluation_repository = evaluation_repository

    @staticmethod
    def _now() -> datetime:
        return datetime.now(UTC)

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
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
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

        # TASK 3: snapshot del resultado de NegotiationEngine si ya existe
        # una VehicleEvaluation con negociación calculada para este
        # vehículo (se pierde en cuanto termina la sesión de búsqueda si
        # no se copia aquí). Best-effort: nunca bloquea la creación del deal.
        if vehicle_id and self.evaluation_repository is not None:
            evaluation = await self.evaluation_repository.get_by_vehicle_id(vehicle_id)
            negotiation = getattr(evaluation, "negotiation", None) if evaluation else None
            if negotiation is not None:
                deal.negotiation_initial_offer = getattr(
                    negotiation, "recommended_initial_offer", None
                )
                deal.negotiation_max_price = getattr(
                    negotiation, "maximum_purchase_price", None
                )
                deal.negotiation_walk_away_price = getattr(
                    negotiation, "walk_away_price", None
                )
                recommendation = getattr(negotiation, "recommendation", None)
                deal.negotiation_recommendation = (
                    recommendation.value
                    if hasattr(recommendation, "value")
                    else recommendation
                )
                deal.negotiation_snapshot_at = self._now()

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
        actual_purchase_price: float | None = None,
        transport_carrier: str | None = None,
        transport_cost: float | None = None,
        registration_plate: str | None = None,
        registration_cost: float | None = None,
        sale_price: float | None = None,
        buyer_name: str | None = None,
        buyer_contact: str | None = None,
    ) -> Deal:
        """Transiciona un deal a un nuevo estado, validando la transición.

        Cada estado de cumplimiento (TASK 3) acepta datos específicos de esa
        etapa, capturados en el momento de la transición:

        - BOUGHT: ``actual_purchase_price`` (si se omite, usa ``offer_price``).
        - IN_TRANSIT: ``transport_carrier``, ``transport_cost`` (opcionales).
        - REGISTERED: ``registration_plate``, ``registration_cost`` (opcionales).
        - SOLD: ``sale_price`` (obligatorio), ``buyer_name``/``buyer_contact``
          (opcionales). Al llegar a SOLD se calcula ``actual_profit`` real
          (no una estimación) a partir de los costes efectivamente
          registrados en el propio deal.

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
            HTTPException 422: Si la transición no es válida, o si falta un
                dato obligatorio para la etapa destino (p.ej. sale_price en SOLD).
        """
        deal = await self.get(deal_id, user_id)

        allowed = self._TRANSITIONS.get(deal.status, set())
        if new_status not in allowed:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=(
                    f"Invalid transition from {deal.status.value} "
                    f"to {new_status.value}"
                ),
            )

        now = self._now()
        deal.status = new_status
        if notes is not None:
            deal.notes = notes
        if offer_price is not None:
            deal.offer_price = offer_price

        if new_status == DealStatus.BOUGHT:
            deal.actual_purchase_price = (
                actual_purchase_price
                if actual_purchase_price is not None
                else deal.offer_price
            )
            deal.bought_at = now

        elif new_status == DealStatus.IN_TRANSIT:
            if transport_carrier is not None:
                deal.transport_carrier = transport_carrier
            if transport_cost is not None:
                deal.transport_cost = transport_cost
            deal.transport_started_at = now

        elif new_status == DealStatus.REGISTERED:
            if registration_plate is not None:
                deal.registration_plate = registration_plate
            if registration_cost is not None:
                deal.registration_cost = registration_cost
            deal.transport_completed_at = deal.transport_completed_at or now
            deal.registered_at = now

        elif new_status == DealStatus.SOLD:
            if sale_price is None or sale_price <= 0:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail="sale_price is required (and must be positive) to mark a deal as SOLD",
                )
            deal.sale_price = sale_price
            if buyer_name is not None:
                deal.buyer_name = buyer_name
            if buyer_contact is not None:
                deal.buyer_contact = buyer_contact
            deal.sold_at = now
            deal.actual_profit = self._compute_actual_profit(deal)

        deal.updated_at = now

        return await self.repository.update(deal)

    @staticmethod
    def _compute_actual_profit(deal: Deal) -> float | None:
        """Beneficio REAL: sale_price - (compra + transporte + matriculación).

        Distinto de ``last_sim_net_profit`` (una estimación previa a la
        venta): este cálculo usa únicamente costes efectivamente registrados
        en el propio deal durante su cumplimiento.
        """
        purchase = (
            deal.actual_purchase_price
            if deal.actual_purchase_price is not None
            else deal.offer_price
        )
        if purchase is None or deal.sale_price is None:
            return None
        total_cost = (
            float(purchase)
            + float(deal.transport_cost or 0)
            + float(deal.registration_cost or 0)
        )
        return round(float(deal.sale_price) - total_cost, 2)

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

    async def delete(self, deal_id: str, user_id: str) -> None:
        """Elimina un deal propio (TASK-021).

        Args:
            deal_id: Id del deal a eliminar.
            user_id: Dueño del deal (ownership check).

        Raises:
            HTTPException 404: Si el deal no existe o no pertenece al usuario.
        """
        deal = await self.get(deal_id, user_id)
        await self.repository.delete(deal)
