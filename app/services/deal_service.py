"""Servicio de gestión de deals (pipeline de ventas) — v2, extendido TASK 3.

Máquina de estados, sin transiciones imposibles:

    NEW         -> ANALYZING | CANCELLED
    ANALYZING   -> NEGOTIATING | LOST | CANCELLED
    NEGOTIATING -> WON | LOST | CANCELLED
    WON         -> BOUGHT | CANCELLED
    BOUGHT      -> IN_TRANSIT | CANCELLED
    IN_TRANSIT  -> REGISTERED | CANCELLED
    REGISTERED  -> SOLD | CANCELLED
    SOLD / LOST / CANCELLED -> terminal (sin salida)

LOST solo es alcanzable antes de WON (fallo de negociación); tras comprar
el vehículo, un trato que no llega a buen fin es CANCELLED, no LOST (ya no
se "pierde" una negociación por algo que ya se compró).

Propiedades garantizadas:

- **Ownership**: cada deal solo es visible/gestionable por su ``user_id``
  (acceso ajeno -> 404, no se filtra existencia).
- **Idempotencia**: transicionar al estado en el que ya está es un no-op
  exitoso (200), no un error; reintentos de red no corrompen el estado.
- **Concurrencia**: la lectura para transicionar bloquea la fila
  (SELECT ... FOR UPDATE) y el ``version`` column añade bloqueo optimista;
  una escritura perdida se traduce a 409 Conflict.
- **Auditoría**: cada creación/transición persiste una fila inmutable en
  ``deal_status_history`` y una entrada en ``audit_logs``, en la MISMA
  transacción que el cambio (todo-o-nada).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import StaleDataError

from app.exceptions.base import (
    DealConcurrentModificationError,
    DealConflictError,
    DealNotFoundError,
    DealValidationError,
)
from app.models.audit_log import AuditLog
from app.models.deal import Deal, DealStatus, DealStatusHistory
from app.repositories.deal_repository import DealRepository
from app.repositories.vehicle_evaluation_repository import VehicleEvaluationRepository

logger = logging.getLogger(__name__)


@dataclass
class DealVariance:
    """Comparación previsto (última simulación) vs. real de un deal.

    Campos ``projected_*`` vienen de ``last_sim_*`` (la última simulación
    guardada, si la hubo); ``actual_*`` vienen de los campos de
    cumplimiento físico (TASK 3). ``None`` cuando el dato aún no existe
    (p.ej. ``actual_total_cost`` antes de BOUGHT, o cualquier campo
    ``projected_*`` si nunca se guardó una simulación).
    """

    deal_id: str
    status: str
    projected_purchase_price: float | None
    actual_purchase_price: float | None
    projected_sale_price: float | None
    actual_sale_price: float | None
    projected_total_cost: float | None
    actual_total_cost: float | None
    projected_net_profit: float | None
    actual_net_profit: float | None
    profit_variance: float | None
    """actual_net_profit - projected_net_profit. Positivo = fue mejor de lo
    previsto. None si falta cualquiera de los dos lados."""
    projected_roi_percentage: float | None


@dataclass
class PortfolioSummary:
    """Reporting de cartera: cerrados (real) + pipeline activo (previsto).

    Los agregados de deals SOLD comparan real contra lo que se había
    previsto en la última simulación guardada de CADA uno de esos deals
    (no una previsión global), así que la comparación es coherente
    aunque perfiles/vehículos sean distintos entre sí.
    """

    by_status: dict[str, int]
    sold_count: int
    sold_actual_profit_sum: float | None
    sold_projected_profit_sum: float | None
    """Suma de last_sim_net_profit de los MISMOS deals que ya están SOLD
    (no de todos los deals históricos): compara lo previsto para estas
    operaciones concretas contra lo que realmente dieron."""
    profit_variance_sum: float | None
    """sold_actual_profit_sum - sold_projected_profit_sum."""
    total_revenue: float | None
    """Suma de sale_price de deals SOLD (cashflow de entrada)."""
    total_invested: float | None
    """Suma de purchase + transport + registration + taxes reales de
    deals SOLD (cashflow de salida ya materializado)."""
    pipeline_count: int
    pipeline_projected_profit: float | None
    """Beneficio previsto (last_sim_net_profit) de deals aún activos
    (NEW..REGISTERED): lo que hay "en juego", no realizado todavía."""


class DealService:
    """Servicio de dominio para el pipeline de deals."""

    # Transiciones válidas por estado actual. Los estados terminales
    # (WON, LOST, CANCELLED) NO tienen salida.
    _TRANSITIONS: dict[DealStatus, set[DealStatus]] = {
        DealStatus.NEW: {DealStatus.ANALYZING, DealStatus.CANCELLED},
        DealStatus.ANALYZING: {
            DealStatus.NEGOTIATING,
            DealStatus.LOST,
            DealStatus.CANCELLED,
        },
        DealStatus.NEGOTIATING: {
            DealStatus.WON,
            DealStatus.LOST,
            DealStatus.CANCELLED,
        },
        DealStatus.WON: {DealStatus.BOUGHT, DealStatus.CANCELLED},
        DealStatus.BOUGHT: {DealStatus.IN_TRANSIT, DealStatus.CANCELLED},
        DealStatus.IN_TRANSIT: {DealStatus.REGISTERED, DealStatus.CANCELLED},
        DealStatus.REGISTERED: {DealStatus.SOLD, DealStatus.CANCELLED},
        # Terminales: SOLD, LOST, CANCELLED no tienen salida.
        DealStatus.SOLD: set(),
        DealStatus.LOST: set(),
        DealStatus.CANCELLED: set(),
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

    @staticmethod
    def allowed_transitions(current: DealStatus) -> set[DealStatus]:
        """Estados destino válidos desde ``current``."""
        return set(DealService._TRANSITIONS.get(current, set()))

    def _audit_entry(
        self,
        *,
        action: str,
        user_id: str,
        deal_id: str,
        details: str,
    ) -> AuditLog:
        """Construye la entrada de auditoría global (sin commitear)."""
        return AuditLog(
            user_id=user_id,
            action=action,
            resource="deal",
            resource_id=deal_id,
            details=details,
            timestamp=self._now(),
        )

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
        (NEW|ANALYZING|NEGOTIATING) para el mismo usuario y oportunidad,
        se rechaza con 409. La condición también está protegida por un
        índice único parcial en BD, así que una carrera entre dos creates
        concurrentes solo permite insertar uno (el perdedor recibe 409).

        Returns:
            El Deal creado con estado NEW e historial inicial persistido.

        Raises:
            HTTPException 422: Si no se proporciona ni opportunity ni vehicle.
            HTTPException 409: Si ya existe un deal activo para la oportunidad.
        """
        if not opportunity_id and not vehicle_id:
            raise DealValidationError(
                "At least one of opportunity_id or vehicle_id is required"
            )

        # Un solo deal activo por opportunity/user. Comprobación optimista;
        # la garantía real la pone uq_deals_active_per_opportunity.
        if opportunity_id:
            existing = await self.repository.get_active_by_opportunity(
                user_id, opportunity_id
            )
            if existing is not None:
                raise DealConflictError(
                    "You already have an active deal for this opportunity",
                    deal_id=existing.id,
                )

        now = self._now()
        deal = Deal(
            user_id=user_id,
            opportunity_id=opportunity_id,
            vehicle_id=vehicle_id,
            status=DealStatus.NEW,
            notes=notes,
            contact_channel=contact_channel,
            status_changed_at=now,
        )

        # TASK 3: snapshot del resultado de NegotiationEngine si ya existe
        # una VehicleEvaluation con negociación calculada para este
        # vehículo (se pierde en cuanto termina la sesión de búsqueda si
        # no se copia aquí). Best-effort: nunca bloquea la creación del deal
        # (un fallo aquí solo deja los campos de negociación en None).
        if vehicle_id and self.evaluation_repository is not None:
            try:
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
            except Exception:  # noqa: BLE001 — snapshot is best-effort here
                logger.warning(
                    "No se pudo tomar el snapshot de negociación para vehicle_id=%s",
                    vehicle_id,
                    exc_info=True,
                )

        creation_history = DealStatusHistory(
            deal_id=deal.id,
            from_status=None,
            to_status=DealStatus.NEW.value,
            changed_by_user_id=user_id,
            notes=notes,
            created_at=now,
        )
        audit = self._audit_entry(
            action="deal_created",
            user_id=user_id,
            deal_id=deal.id,
            details=f"Deal created from "
            f"{'opportunity ' + opportunity_id if opportunity_id else 'vehicle'}"
            f"{' ' + str(vehicle_id) if vehicle_id else ''}",
        )
        try:
            return await self.repository.save_transition(deal, creation_history, audit)
        except IntegrityError as exc:
            raise DealConflictError(
                "You already have an active deal for this opportunity"
            ) from exc

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
            DealNotFoundError 404: Si el deal no existe o no pertenece al usuario.
        """
        deal = await self.repository.get_by_id(deal_id)
        if deal is None or deal.user_id != user_id:
            raise DealNotFoundError("Deal not found")
        return deal

    async def get_history(
        self,
        deal_id: str,
        user_id: str,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[DealStatusHistory], int]:
        """Devuelve el historial de estados de un deal propio (auditoría)."""
        await self.get(deal_id, user_id)
        return await self.repository.list_history(deal_id, limit=limit, offset=offset)

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
        actual_taxes: float | None = None,
        sale_price: float | None = None,
        buyer_name: str | None = None,
        buyer_contact: str | None = None,
    ) -> Deal:
        """Transiciona un deal validando la máquina de estados.

        - Idempotente: si ``new_status == deal.status`` devuelve el deal
          sin escribir nada (reintentos seguros).
        - Concurrencia: lee con FOR UPDATE + bloqueo optimista por versión;
          conflicto -> 409.
        - Atómico: deal + historial + audit log en una sola transacción.
        - Cada estado de cumplimiento físico (TASK 3) acepta datos
          específicos de esa etapa, capturados en el momento de la
          transición:

          - BOUGHT: ``actual_purchase_price`` (si se omite, usa ``offer_price``).
          - IN_TRANSIT: ``transport_carrier``, ``transport_cost`` (opcionales).
          - REGISTERED: ``registration_plate``, ``registration_cost``,
            ``actual_taxes`` (IEDMT + IVA reales, opcionales).
          - SOLD: ``sale_price`` (obligatorio), ``buyer_name``/``buyer_contact``
            (opcionales). Al llegar a SOLD se calcula ``actual_profit`` real
            (no una estimación) a partir de los costes efectivamente
            registrados en el propio deal.

        Args:
            deal_id: Id del deal a transicionar.
            user_id: Dueño del deal (ownership check).
            new_status: Estado destino.
            notes: Notas opcionales a añadir/actualizar.
            offer_price: Precio de oferta opcional (p.ej. en NEGOTIATING/WON).

        Returns:
            El Deal actualizado.

        Raises:
            DealNotFoundError 404: Si el deal no existe o no pertenece al usuario.
            DealValidationError 422: Si la transición no es válida, o si falta
                un dato obligatorio para la etapa destino (p.ej. sale_price en
                SOLD).
            DealConcurrentModificationError 409: Si otra escritura ganó la carrera.
        """
        if offer_price is not None and offer_price < 0:
            raise DealValidationError("offer_price must be >= 0")

        deal = await self.repository.get_by_id(deal_id, for_update=True)
        if deal is None or deal.user_id != user_id:
            raise DealNotFoundError("Deal not found")

        current_status = deal.status

        # Idempotencia: pedir el estado actual es un no-op exitoso.
        if new_status == current_status:
            return deal

        allowed = self._TRANSITIONS.get(current_status, set())
        if new_status not in allowed:
            raise DealValidationError(
                f"Invalid transition from {current_status.value} "
                f"to {new_status.value}"
            )

        old_status_value = current_status.value
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
            if actual_taxes is not None:
                deal.actual_taxes = actual_taxes
            deal.transport_completed_at = deal.transport_completed_at or now
            deal.registered_at = now

        elif new_status == DealStatus.SOLD:
            if sale_price is None or sale_price <= 0:
                raise DealValidationError(
                    "sale_price is required (and must be positive) to mark a deal as SOLD"
                )
            deal.sale_price = sale_price
            if buyer_name is not None:
                deal.buyer_name = buyer_name
            if buyer_contact is not None:
                deal.buyer_contact = buyer_contact
            deal.sold_at = now
            deal.actual_profit = self._compute_actual_profit(deal)

        deal.status_changed_at = now
        deal.closed_at = now if new_status.is_terminal else None
        deal.updated_at = now

        history = DealStatusHistory(
            deal_id=deal.id,
            from_status=old_status_value,
            to_status=new_status.value,
            changed_by_user_id=user_id,
            notes=notes,
            offer_price=offer_price,
            created_at=now,
        )
        audit = self._audit_entry(
            action="deal_status_changed",
            user_id=user_id,
            deal_id=deal.id,
            details=f"status: {old_status_value} -> {new_status.value}",
        )
        try:
            return await self.repository.save_transition(deal, history, audit)
        except StaleDataError as exc:
            # Otra petición modificó el deal mientras esta transición
            # estaba en vuelo: el cliente debe releer y reintentar.
            raise DealConcurrentModificationError(
                "Deal was modified concurrently, please retry"
            ) from exc

    @staticmethod
    def _compute_actual_profit(deal: Deal) -> float | None:
        """Beneficio REAL: sale_price - (compra + transporte + matriculación
        + impuestos reales).

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
            + float(deal.actual_taxes or 0)
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
        """Elimina un deal propio (TASK-021). El historial se borra en cascada."""
        deal = await self.get(deal_id, user_id)
        audit = self._audit_entry(
            action="deal_deleted",
            user_id=user_id,
            deal_id=deal.id,
            details=f"Deal deleted while in status {deal.status.value}",
        )
        await self.repository.delete(deal, audit)

    # ------------------------------------------------------------------
    # Reporting: previsto vs. real, cartera
    # ------------------------------------------------------------------

    async def get_deal_variance(self, deal_id: str, user_id: str) -> DealVariance:
        """Compara la última simulación guardada de un deal contra lo real.

        Raises:
            DealNotFoundError 404: Si el deal no existe o no pertenece al usuario.
        """
        deal = await self.get(deal_id, user_id)

        actual_total_cost: float | None = None
        purchase_for_cost = (
            deal.actual_purchase_price
            if deal.actual_purchase_price is not None
            else deal.offer_price
        )
        if purchase_for_cost is not None:
            actual_total_cost = round(
                float(purchase_for_cost)
                + float(deal.transport_cost or 0)
                + float(deal.registration_cost or 0)
                + float(deal.actual_taxes or 0),
                2,
            )

        profit_variance = None
        if deal.actual_profit is not None and deal.last_sim_net_profit is not None:
            profit_variance = round(
                float(deal.actual_profit) - float(deal.last_sim_net_profit), 2
            )

        return DealVariance(
            deal_id=deal.id,
            status=deal.status.value,
            projected_purchase_price=deal.last_sim_purchase_price,
            actual_purchase_price=deal.actual_purchase_price,
            projected_sale_price=deal.last_sim_sale_price,
            actual_sale_price=deal.sale_price,
            projected_total_cost=deal.last_sim_total_cost,
            actual_total_cost=actual_total_cost,
            projected_net_profit=deal.last_sim_net_profit,
            actual_net_profit=deal.actual_profit,
            profit_variance=profit_variance,
            projected_roi_percentage=deal.last_sim_roi,
        )

    async def get_portfolio_summary(self, user_id: str) -> PortfolioSummary:
        """Reporting de cartera del usuario: cerrados (real vs. previsto) +
        pipeline activo (previsto, aún no realizado).
        """
        agg = await self.repository.get_portfolio_aggregates(user_id)

        sold_actual = agg["sold_actual_profit_sum"]
        sold_projected = agg["sold_projected_profit_sum"]
        profit_variance_sum = None
        if sold_actual is not None and sold_projected is not None:
            profit_variance_sum = round(float(sold_actual) - float(sold_projected), 2)

        total_invested = None
        cost_parts = [
            agg["sold_purchase_sum"],
            agg["sold_transport_sum"],
            agg["sold_registration_sum"],
            agg["sold_taxes_sum"],
        ]
        if any(part is not None for part in cost_parts):
            total_invested = round(sum(float(p or 0) for p in cost_parts), 2)

        return PortfolioSummary(
            by_status=agg["by_status"],
            sold_count=agg["sold_count"],
            sold_actual_profit_sum=(
                round(float(sold_actual), 2) if sold_actual is not None else None
            ),
            sold_projected_profit_sum=(
                round(float(sold_projected), 2) if sold_projected is not None else None
            ),
            profit_variance_sum=profit_variance_sum,
            total_revenue=(
                round(float(agg["sold_revenue_sum"]), 2)
                if agg["sold_revenue_sum"] is not None
                else None
            ),
            total_invested=total_invested,
            pipeline_count=agg["pipeline_count"],
            pipeline_projected_profit=(
                round(float(agg["pipeline_projected_profit_sum"]), 2)
                if agg["pipeline_projected_profit_sum"] is not None
                else None
            ),
        )
