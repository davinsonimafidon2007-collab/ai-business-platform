"""API endpoints for opportunities (Task C.1)."""

from __future__ import annotations

import csv
import io
from datetime import UTC, date, datetime, time

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.deal import DealRead
from app.api.v1.schemas.opportunity import (
    OpportunityCreate,
    OpportunityListResponse,
    OpportunityRead,
    OpportunityReadDetail,
    OpportunityUpdate,
    OpportunityVehicleSummary,
)
from app.database import get_db_session
from app.dependencies.auth import get_current_user
from app.models.opportunity import Opportunity
from app.models.user import User
from app.models.vehicle import Vehicle
from app.repositories.deal_repository import DealRepository
from app.repositories.opportunity_repository import OpportunityRepository
from app.repositories.vehicle_evaluation_repository import VehicleEvaluationRepository
from app.schemas.pagination import CursorPage
from app.services.deal_service import DealService
from app.services.opportunity_integration_service import OpportunityIntegrationService
from app.services.opportunity_phase_service import OpportunityPhaseService
from app.services.recommendation_labels import recommendation_label_es, risk_label_es

router = APIRouter(prefix="/opportunities", tags=["Opportunities"])

_CSV_HEADERS = [
    "id",
    "vehicle_id",
    "source",
    "external_id",
    "url",
    "brand",
    "model",
    "year",
    "mileage",
    "price",
    "score",
    "estimated_profit",
    "roi_percentage",
    "recommendation",
    "risk_level",
    "created_at",
]


def _csv_row(opp: Opportunity) -> list:
    v = opp.vehicle
    return [
        opp.id,
        opp.vehicle_id,
        v.source if v else "",
        v.external_id if v else "",
        v.url if v else "",
        v.brand if v else "",
        v.model if v else "",
        v.year if v else "",
        v.mileage if v else "",
        v.price if v else "",
        opp.opportunity_score if opp.opportunity_score is not None else "",
        opp.profit if opp.profit is not None else "",
        opp.roi if opp.roi is not None else "",
        opp.recommendation or "",
        opp.risk or "",
        opp.created_at.isoformat() if opp.created_at else "",
    ]


def _csv_stream(opps: list[Opportunity]) -> StreamingResponse:
    """Serializa las oportunidades a CSV UTF-8 con BOM (para Excel)."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\r\n")
    writer.writerow(_CSV_HEADERS)
    for opp in opps:
        writer.writerow(_csv_row(opp))

    raw = buffer.getvalue()
    bytes_io = io.BytesIO(b"\xef\xbb\xbf" + raw.encode("utf-8"))
    return StreamingResponse(
        bytes_io,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="oportunidades.csv"',
        },
    )


def _to_opportunity_read(opp: Opportunity) -> OpportunityRead:
    """Mapea un Opportunity (eager-loaded vehicle) a OpportunityRead."""
    vehicle = opp.vehicle
    vehicle_summary = None
    if vehicle is not None:
        vehicle_summary = OpportunityVehicleSummary(
            id=vehicle.id,
            brand=vehicle.brand,
            model=vehicle.model,
            year=vehicle.year,
            mileage=vehicle.mileage,
            price=vehicle.price,
            source=vehicle.source,
            external_id=vehicle.external_id,
            url=vehicle.url,
        )
    return OpportunityRead(
        id=opp.id,
        vehicle=vehicle_summary,
        score=opp.opportunity_score,
        estimated_profit=opp.profit,
        roi_percentage=opp.roi,
        recommendation=opp.recommendation,
        risk_level=opp.risk,
        confidence=opp.confidence,
        status=opp.status,
        recommendation_label_es=recommendation_label_es(opp.recommendation),
        risk_label_es=risk_label_es(opp.risk),
        created_at=opp.created_at,
        updated_at=opp.analyzed_at,
    )


@router.get("", response_model=OpportunityListResponse)
async def list_opportunities(
    recommendation: str | None = Query(
        None, description="Filtro por recomendación (BUY_NOW, WATCH, NEGOTIATE, REJECT)"
    ),
    min_score: float | None = Query(None, ge=0, description="Score mínimo (0-100)"),
    min_roi: float | None = Query(None, description="ROI mínimo (%)"),
    opportunity_status: str | None = Query(
        None,
        alias="status",
        description="Filtro por estado de la oportunidad (OPEN, CONVERTED)",
    ),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> OpportunityListResponse:
    """Lista oportunidades de importación del usuario autenticado.

    Devuelve oportunidades paginadas con score, profit, ROI, recomendación
    y resumen del vehículo asociado. Filtros opcionales por recomendación,
    score mínimo, ROI mínimo y estado (AUD-010: antes se aceptaba el filtro
    pero nunca se aplicaba).
    """
    repo = OpportunityRepository(session)
    items, total = await repo.list_filtered(
        user_id=current_user.id,
        recommendation=recommendation,
        min_score=min_score,
        min_roi=min_roi,
        status=opportunity_status,
        limit=limit,
        offset=offset,
    )

    mapped: list[OpportunityRead] = [_to_opportunity_read(opp) for opp in items]

    return OpportunityListResponse(
        items=mapped,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/cursor", response_model=CursorPage[OpportunityRead])
async def list_opportunities_cursor(
    cursor: str | None = Query(None, description="Token de la página anterior"),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> CursorPage[OpportunityRead]:
    """Lista oportunidades del usuario con paginación por cursor (TASK-019)."""
    repo = OpportunityRepository(session)
    items, total, has_more, next_cursor = await repo.list_cursor(
        cursor=cursor,
        limit=limit,
        user_id=current_user.id,
    )
    return CursorPage[OpportunityRead](
        items=[_to_opportunity_read(opp) for opp in items],
        total=total,
        has_more=has_more,
        next_cursor=next_cursor,
        limit=limit,
    )


@router.get("/export/csv")
async def export_opportunities_csv(
    date_from: date | None = Query(
        None, description="Fecha inicial (YYYY-MM-DD, inclusiva, hora local)"
    ),
    date_to: date | None = Query(
        None, description="Fecha final (YYYY-MM-DD, inclusiva, hora local)"
    ),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> StreamingResponse:
    """Exporta las oportunidades del usuario a CSV UTF-8 (TASK-018).

    Filtros opcionales por rango de fechas (created_at). El CSV incluye BOM
    para abrirse bien en Excel.
    """
    start_dt: datetime | None = None
    end_dt: datetime | None = None
    if date_from is not None:
        start_dt = datetime.combine(date_from, time.min).replace(tzinfo=UTC)
    if date_to is not None:
        end_dt = datetime.combine(date_to, time.max).replace(tzinfo=UTC)

    repo = OpportunityRepository(session)
    opps = await repo.list_export(
        user_id=current_user.id,
        date_from=start_dt,
        date_to=end_dt,
    )
    return _csv_stream(opps)


async def _get_owned_opportunity(
    session: AsyncSession,
    user_id: str,
    opportunity_id: str,
) -> Opportunity:
    """Obtiene una oportunidad validando ownership por join con el vehículo.

    La tabla ``opportunities`` no tiene ``user_id``; la propiedad se resuelve
    por el vehículo asociado (misma regla que ``list_filtered``). Devuelve la
    oportunidad con el vehículo eager-loaded o lanza 404.
    """
    result = await session.execute(
        select(Opportunity)
        .join(Vehicle, Vehicle.id == Opportunity.vehicle_id)
        .where(
            Opportunity.id == opportunity_id,
            Vehicle.user_id == user_id,
        )
    )
    opportunity = result.scalar_one_or_none()
    if opportunity is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Opportunity not found",
        )
    return opportunity


@router.post("", response_model=OpportunityRead, status_code=status.HTTP_201_CREATED)
async def create_opportunity(
    payload: OpportunityCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> OpportunityRead:
    """Registra una oportunidad manualmente (TASK-021).

    Requiere un ``vehicle_id`` que pertenezca al usuario autenticado. Los
    campos analíticos (score, ROI, recomendación, riesgo, beneficio) se
    guardan tal cual se reciben.
    """
    vehicle_result = await session.execute(
        select(Vehicle.id).where(
            Vehicle.id == payload.vehicle_id,
            Vehicle.user_id == current_user.id,
        )
    )
    if vehicle_result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehicle not found",
        )

    opportunity = Opportunity(
        vehicle_id=payload.vehicle_id,
        opportunity_score=payload.score,
        profit=payload.estimated_profit,
        roi=payload.roi_percentage,
        recommendation=payload.recommendation,
        risk=payload.risk_level,
        engine_version=payload.engine_version,
        analyzed_at=datetime.now(UTC),
    )
    opportunity = await OpportunityRepository(session).save(opportunity)
    return _to_opportunity_read(opportunity)


class OpportunityConvertToDealRequest(BaseModel):
    """Cuerpo opcional para convertir una oportunidad en deal."""

    notes: str | None = Field(
        default=None, description="Notas iniciales para el deal creado"
    )


@router.post(
    "/{opportunity_id}/convert-to-deal",
    response_model=DealRead,
    status_code=status.HTTP_201_CREATED,
)
async def convert_opportunity_to_deal(
    opportunity_id: str,
    payload: OpportunityConvertToDealRequest | None = None,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> DealRead:
    """Convierte una oportunidad en un deal (TASK 3 / AUD-011).

    Cierra el flujo listing -> opportunity -> deal: solo funciona sobre
    oportunidades con recomendación BUY_NOW o NEGOTIATE (422 en otro caso),
    y solo una vez por oportunidad (409 si ya se convirtió, o si ya hay un
    deal activo para ella).
    """
    integration = OpportunityIntegrationService(
        opportunity_repository=OpportunityRepository(session),
        deal_service=DealService(
            DealRepository(session), VehicleEvaluationRepository(session)
        ),
    )
    deal = await integration.convert_to_deal(
        opportunity_id=opportunity_id,
        user_id=current_user.id,
        notes=payload.notes if payload else None,
    )
    return DealRead.model_validate(deal)


@router.patch("/{opportunity_id}", response_model=OpportunityRead)
async def update_opportunity(
    opportunity_id: str,
    payload: OpportunityUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> OpportunityRead:
    """Actualiza los campos analíticos de una oportunidad propia (TASK-021)."""
    opportunity = await _get_owned_opportunity(
        session, current_user.id, opportunity_id
    )

    updates = {
        "opportunity_score": payload.score,
        "profit": payload.estimated_profit,
        "roi": payload.roi_percentage,
        "recommendation": payload.recommendation,
        "risk": payload.risk_level,
    }
    for attr, value in updates.items():
        if value is not None:
            setattr(opportunity, attr, value)

    await session.commit()
    await session.refresh(opportunity)
    return _to_opportunity_read(opportunity)


@router.delete("/{opportunity_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_opportunity(
    opportunity_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> None:
    """Elimina una oportunidad propia (TASK-021)."""
    opportunity = await _get_owned_opportunity(
        session, current_user.id, opportunity_id
    )
    await OpportunityRepository(session).delete(opportunity)


@router.get("/{opportunity_id}", response_model=OpportunityReadDetail)
async def get_opportunity_detail(
    opportunity_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> OpportunityReadDetail:
    """Obtiene una oportunidad propia con detalle ampliado (incluye fases)."""
    await _get_owned_opportunity(session, current_user.id, opportunity_id)
    opportunity = await OpportunityRepository(session).get(opportunity_id)
    if opportunity is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Opportunity not found",
        )

    phase_service = OpportunityPhaseService(session)
    phases = await phase_service.ensure_seeded(opportunity)

    # Se reutiliza el mismo mapper que el listado para que detalle y listado
    # no diverjan (antes el detalle omitía confidence y status).
    base = _to_opportunity_read(opportunity)
    return OpportunityReadDetail(
        # recommendation_label/risk_label son computed_field: no se pueden
        # pasar al constructor, se recalculan solas.
        **base.model_dump(exclude={"recommendation_label", "risk_label"}),
        phases=[OpportunityPhaseService.to_read(p) for p in phases],
    )


# ------------------------------------------------------------------
# Workflow phases
# ------------------------------------------------------------------

@router.get("/{opportunity_id}/phases")
async def list_opportunity_phases(
    opportunity_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[dict]:
    """Lista las fases del workflow de una oportunidad propia.

    Si aún no existen, se siembran automáticamente las fases por defecto.
    """
    await _get_owned_opportunity(session, current_user.id, opportunity_id)
    service = OpportunityPhaseService(session)
    opportunity = await OpportunityRepository(session).get(opportunity_id)
    if opportunity is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Opportunity not found",
        )
    phases = await service.ensure_seeded(opportunity)
    return [OpportunityPhaseService.to_read(p) for p in phases]


class OpportunityFeedbackCreate(BaseModel):
    """Cuerpo para registrar feedback/notas sobre una oportunidad."""
    feedback: str = Field(..., min_length=1, description="Notas o retroalimentación sobre la oportunidad")


@router.post("/{opportunity_id}/feedback", response_model=OpportunityRead)
async def create_opportunity_feedback(
    opportunity_id: str,
    payload: OpportunityFeedbackCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> OpportunityRead:
    """Registra feedback/notas sobre una oportunidad propia.

    Por simplicidad, almacena el feedback creando una fase de workflow
    especial con el texto recibido, reutilizando la tabla existente.
    """
    await _get_owned_opportunity(session, current_user.id, opportunity_id)
    opportunity = await OpportunityRepository(session).get(opportunity_id)
    if opportunity is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Opportunity not found",
        )

    phase_service = OpportunityPhaseService(session)
    await phase_service.ensure_seeded(opportunity)
    # Crear una fase de feedback con el texto recibido.
    await phase_service.apply_action(
        opportunity=opportunity,
        phase_id="feedback",
        action="start",
        feedback=payload.feedback,
    )
    # Devolver la oportunidad actualizada.
    refreshed = await OpportunityRepository(session).get(opportunity_id)
    return _to_opportunity_read(refreshed or opportunity)


@router.patch("/{opportunity_id}/phases/{phase_id}")
async def patch_opportunity_phase(
    opportunity_id: str,
    phase_id: str,
    body: dict,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """Ejecuta una acción sobre una fase del workflow.

    Body esperado: ``{ "action": "approve" | "reject" | "request_changes" | "start", "feedback": "..." }``
    """
    await _get_owned_opportunity(session, current_user.id, opportunity_id)
    action = str(body.get("action", "")).strip().lower()
    feedback = body.get("feedback")
    service = OpportunityPhaseService(session)
    opportunity = await OpportunityRepository(session).get(opportunity_id)
    if opportunity is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Opportunity not found",
        )
    await service.ensure_seeded(opportunity)
    phase = await service.apply_action(
        opportunity=opportunity,
        phase_id=phase_id,
        action=action,
        feedback=feedback,
    )
    return OpportunityPhaseService.to_read(phase)
