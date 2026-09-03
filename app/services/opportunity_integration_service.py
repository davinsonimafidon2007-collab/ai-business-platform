"""Opportunity Integration Service — conecta Opportunity con el pipeline de Deal.

TASK 3 (AUD-011): reescrito desde cero. La versión anterior (`analyze_and_
create_deal`) era código muerto e inalcanzable — llamaba `.get()` sobre un
`OpportunityAnalysis` (dataclass, no dict) y pasaba un `vehicle_id` como si
fuera `opportunity_id`, violando la FK si alguna vez se hubiese invocado.

Esta versión opera sobre una `Opportunity` ya persistida y analizada (no
vuelve a ejecutar el análisis), y es la transición real y funcional entre
"tengo una oportunidad" y "tengo un deal para gestionarla".
"""

from __future__ import annotations

from fastapi import HTTPException, status

from app.models.deal import Deal
from app.models.opportunity import OpportunityStatus
from app.repositories.opportunity_repository import OpportunityRepository
from app.services.deal_service import DealService

# Recomendaciones de OpportunityFinder que justifican convertir la
# oportunidad en un deal a gestionar. WATCH/REJECT no lo son: una
# oportunidad a vigilar o descartada no debería generar trabajo de gestión.
_CONVERTIBLE_RECOMMENDATIONS: frozenset[str] = frozenset({"BUY_NOW", "NEGOTIATE"})


class OpportunityIntegrationService:
    """Integra el análisis de oportunidades con el pipeline de deals."""

    def __init__(
        self,
        opportunity_repository: OpportunityRepository,
        deal_service: DealService,
    ) -> None:
        self.opportunity_repository = opportunity_repository
        self.deal_service = deal_service

    async def convert_to_deal(
        self,
        *,
        opportunity_id: str,
        user_id: str,
        notes: str | None = None,
    ) -> Deal:
        """Crea un Deal a partir de una Opportunity ya analizada.

        Cierra el hueco listing -> opportunity -> deal: antes de esto, la
        creación de deals era 100% manual (POST /deals con un opportunity_id
        elegido a mano por el usuario/frontend). Este método hace la misma
        operación pero partiendo de la oportunidad, con las validaciones de
        negocio correctas.

        Args:
            opportunity_id: Oportunidad de origen (debe pertenecer a un
                vehículo del usuario).
            user_id: Dueño (ownership check vía el vehículo de la oportunidad).
            notes: Notas iniciales opcionales para el deal creado.

        Returns:
            El Deal recién creado (estado NEW).

        Raises:
            HTTPException 404: Oportunidad inexistente o de otro usuario.
            HTTPException 409: La oportunidad ya fue convertida antes, o ya
                existe un deal activo para ella (delegado en DealService.create).
            HTTPException 422: La recomendación de la oportunidad (WATCH/
                REJECT) no justifica crear un deal.
        """
        opportunity = await self.opportunity_repository.get(opportunity_id)
        if opportunity is None or opportunity.vehicle is None or (
            opportunity.vehicle.user_id != user_id
        ):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Opportunity not found",
            )

        if opportunity.status == OpportunityStatus.CONVERTED.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This opportunity was already converted to a deal",
            )

        if opportunity.recommendation not in _CONVERTIBLE_RECOMMENDATIONS:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=(
                    f"Opportunity recommendation ({opportunity.recommendation!r}) "
                    "does not warrant creating a deal; only BUY_NOW/NEGOTIATE do"
                ),
            )

        deal = await self.deal_service.create(
            user_id=user_id,
            opportunity_id=opportunity.id,
            vehicle_id=opportunity.vehicle_id,
            notes=notes
            or f"Creado desde oportunidad ({opportunity.recommendation})",
        )

        # DealService.create ya validó que no hubiera un deal activo (409);
        # si llegamos aquí, marcar la oportunidad como convertida para que
        # no pueda generar un segundo deal más adelante.
        opportunity.status = OpportunityStatus.CONVERTED.value
        await self.opportunity_repository.save(opportunity)

        return deal
