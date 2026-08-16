"""API endpoints for opportunities (Task C.1)."""

from __future__ import annotations

import csv
import io
from datetime import UTC, date, datetime, time

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.opportunity import (
    OpportunityListResponse,
    OpportunityRead,
    OpportunityVehicleSummary,
)
from app.database import get_db_session
from app.dependencies.auth import get_current_user
from app.models.opportunity import Opportunity
from app.models.user import User
from app.repositories.opportunity_repository import OpportunityRepository
from app.schemas.pagination import CursorPage
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
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> OpportunityListResponse:
    """Lista oportunidades de importación del usuario autenticado.

    Devuelve oportunidades paginadas con score, profit, ROI, recomendación
    y resumen del vehículo asociado. Filtros opcionales por recomendación,
    score mínimo y ROI mínimo.
    """
    repo = OpportunityRepository(session)
    items, total = await repo.list_filtered(
        user_id=current_user.id,
        recommendation=recommendation,
        min_score=min_score,
        min_roi=min_roi,
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