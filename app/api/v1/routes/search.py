"""Search endpoints.

POST /search — Executes a full vehicle search with analysis pipeline.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, status

from app.api.v1.dependencies import get_search_engine_service
from app.api.v1.schemas.common import (
    CostBreakdownSchema,
    MarketEstimationSchema,
    OpportunityAnalysisSchema,
    ProfitAnalysisSchema,
    VehicleScoreSchema,
)
from app.api.v1.schemas.negotiation import (
    NegotiationArgumentSchema,
    NegotiationResultSchema,
    NegotiationScriptSchema,
)
from app.api.v1.schemas.search import (
    ProviderIssueSchema,
    SearchAPIRequest,
    SearchAPIResponse,
    SearchResultItem,
    SearchSummarySchema,
)
from app.dependencies.auth import require_search
from app.models.user import User
from app.services.cost_breakdown_labels import build_cost_lines
from app.services.metrics_service import record_opportunity_generated, record_search_request
from app.services.profit_coherence import build_coherence_warnings
from app.services.provider_issue_labels import build_provider_issue_payloads
from app.services.recommendation_labels import recommendation_label_es, risk_label_es
from app.services.search_engine import SearchEngineService

router = APIRouter(tags=["Search"])


def _provider_sources_from_me(me: Any) -> list[str]:
    src = getattr(me, "provider_sources", None)
    if src:
        return list(src)
    notes = getattr(me, "notes", None) or []
    for n in notes:
        if isinstance(n, str) and n.startswith("providers="):
            raw = n.split("=", 1)[1].strip()
            return [p for p in raw.split(",") if p]
    return []


def _build_search_result_item(result: Any) -> SearchResultItem:
    """Convierte un SearchResult interno en un SearchResultItem de la API.

    Args:
        result: Un SearchResult del dominio (contiene vehicle, vehicle_score,
            market_estimation, profit_analysis, opportunity).

    Returns:
        SearchResultItem listo para serializar como JSON.
    """
    vehicle = result.vehicle

    # --- Datos básicos del vehículo ---
    images: list[str] = []
    if hasattr(vehicle, "images") and vehicle.images:
        if isinstance(vehicle.images, list):
            images = vehicle.images
        elif isinstance(vehicle.images, str):
            images = [img.strip() for img in vehicle.images.split(",") if img.strip()]

    # --- VehicleScore ---
    vs = result.vehicle_score
    vehicle_score_schema: VehicleScoreSchema | None = None
    if vs is not None:
        from app.services.vehicle_scorer import SCORE_CATEGORY_KEY_FROM_ES, SCORE_CATEGORY_LABELS_ES

        strengths: list[str] = getattr(vs, "strengths", []) or []
        weaknesses: list[str] = getattr(vs, "weaknesses", []) or []
        raw_category = getattr(vs, "category", "") or ""
        category_key = getattr(vs, "category_key", None) or SCORE_CATEGORY_KEY_FROM_ES.get(
            raw_category, "poor"
        )
        category_label_es = (
            getattr(vs, "category_label_es", None)
            or SCORE_CATEGORY_LABELS_ES.get(category_key, raw_category)
            or raw_category
        )

        vehicle_score_schema = VehicleScoreSchema(
            score=getattr(vs, "score", 0) or 0,
            category=raw_category or category_label_es,
            category_key=category_key,
            category_label_es=category_label_es,
            strengths=strengths,
            weaknesses=weaknesses,
        )

    # --- MarketEstimation ---
    me = result.market_estimation
    market_estimation_schema: MarketEstimationSchema | None = None
    if me is not None:
        notes: list[str] = getattr(me, "notes", []) or []
        market_estimation_schema = MarketEstimationSchema(
            market_price=getattr(me, "market_price", 0.0) or 0.0,
            confidence=getattr(me, "confidence", 0.0) or 0.0,
            supply_level=getattr(me, "supply_level", 50.0) or 50.0,
            demand_level=getattr(me, "demand_level", 50.0) or 50.0,
            market_trend=getattr(me, "market_trend", "stable") or "stable",
            comparable_count=getattr(me, "comparable_count", 0) or 0,
            notes=notes,
            explanation=getattr(me, "explanation", "") or "",
            provider_sources=_provider_sources_from_me(me),
        )

    # --- ProfitAnalysis ---
    pa = result.profit_analysis
    profit_analysis_schema: ProfitAnalysisSchema | None = None
    if pa is not None:
        # CostBreakdown
        cb = getattr(pa, "cost_breakdown", None)
        cost_breakdown_schema: CostBreakdownSchema | None = None
        if cb is not None:
            cost_lines = build_cost_lines(cb)
            cost_breakdown_schema = CostBreakdownSchema(
                purchase_price=getattr(cb, "purchase_price", 0.0) or 0.0,
                transport_cost=getattr(cb, "transport_cost", 0.0) or 0.0,
                registration_cost=getattr(cb, "registration_cost", 0.0) or 0.0,
                taxes=getattr(cb, "taxes", 0.0) or 0.0,
                inspection_cost=getattr(cb, "inspection_cost", 0.0) or 0.0,
                repair_estimate=getattr(cb, "repair_estimate", 0.0) or 0.0,
                commission_cost=getattr(cb, "commission_cost", 0.0) or 0.0,
                miscellaneous_cost=getattr(cb, "miscellaneous_cost", 0.0) or 0.0,
                total_fixed_costs=getattr(cb, "total_fixed_costs", 0.0) or 0.0,
                total_variable_costs=getattr(cb, "total_variable_costs", 0.0) or 0.0,
                total_cost=getattr(cb, "total_cost", 0.0) or 0.0,
                cost_lines=cost_lines,
            )

        risk_level = getattr(pa, "risk_level", None)
        if risk_level is not None:
            risk_level = risk_level.value if hasattr(risk_level, "value") else str(risk_level)

        recommendation = getattr(pa, "recommendation", None)
        if recommendation is not None:
            recommendation = recommendation.value if hasattr(recommendation, "value") else str(recommendation)

        # ROI.1 — Avisos de coherencia (no bloqueantes, solo señales)
        market_price = None
        if me is not None:
            market_price = getattr(me, "market_price", None)
        if market_price is not None and market_price <= 0:
            market_price = None
        coherence_warnings = build_coherence_warnings(
            purchase_price=getattr(pa, "purchase_price", None),
            total_cost=getattr(pa, "total_cost", None),
            estimated_profit=getattr(pa, "net_profit", None),
            roi=getattr(pa, "roi_percentage", None),
            market_price=market_price,
        )

        profit_analysis_schema = ProfitAnalysisSchema(
            purchase_price=getattr(pa, "purchase_price", 0.0) or 0.0,
            transport_cost=getattr(pa, "transport_cost", 0.0) or 0.0,
            registration_cost=getattr(pa, "registration_cost", 0.0) or 0.0,
            taxes=getattr(pa, "taxes", 0.0) or 0.0,
            inspection_cost=getattr(pa, "inspection_cost", 0.0) or 0.0,
            repair_estimate=getattr(pa, "repair_estimate", 0.0) or 0.0,
            commission_cost=getattr(pa, "commission_cost", 0.0) or 0.0,
            miscellaneous_cost=getattr(pa, "miscellaneous_cost", 0.0) or 0.0,
            total_cost=getattr(pa, "total_cost", 0.0) or 0.0,
            estimated_sale_price=getattr(pa, "estimated_sale_price", 0.0) or 0.0,
            gross_profit=getattr(pa, "gross_profit", 0.0) or 0.0,
            net_profit=getattr(pa, "net_profit", 0.0) or 0.0,
            roi_percentage=getattr(pa, "roi_percentage", 0.0) or 0.0,
            profit_margin_percentage=getattr(pa, "profit_margin_percentage", 0.0) or 0.0,
            risk_level=risk_level or "UNKNOWN",
            recommendation=recommendation or "UNKNOWN",
            recommendation_label_es=recommendation_label_es(recommendation or "UNKNOWN"),
            risk_label_es=risk_label_es(risk_level or "UNKNOWN"),
            coherence_warnings=coherence_warnings,
            cost_breakdown=cost_breakdown_schema or CostBreakdownSchema(
                purchase_price=0.0, transport_cost=0.0, registration_cost=0.0,
                taxes=0.0, inspection_cost=0.0, repair_estimate=0.0,
                commission_cost=0.0, miscellaneous_cost=0.0, total_cost=0.0,
            ),
        )

    # --- OpportunityAnalysis ---
    opp = result.opportunity
    opportunity_schema: OpportunityAnalysisSchema | None = None
    if opp is not None:
        opp_strengths: list[str] = getattr(opp, "strengths", []) or []
        opp_weaknesses: list[str] = getattr(opp, "weaknesses", []) or []

        opp_level = getattr(opp, "opportunity_level", None)
        opp_level_str = opp_level.value if hasattr(opp_level, "value") else str(opp_level or "UNKNOWN")

        opp_rec = getattr(opp, "recommendation", None)
        opp_rec_str = opp_rec.value if hasattr(opp_rec, "value") else str(opp_rec or "UNKNOWN")

        opportunity_schema = OpportunityAnalysisSchema(
            overall_score=getattr(opp, "overall_score", 0.0) or 0.0,
            opportunity_level=opp_level_str,
            recommendation=opp_rec_str,
            recommendation_label_es=recommendation_label_es(opp_rec_str),
            estimated_profit=getattr(opp, "estimated_profit", 0.0) or 0.0,
            roi=getattr(opp, "roi", 0.0) or 0.0,
            market_confidence=getattr(opp, "market_confidence", 0.0) or 0.0,
            risk_level=getattr(opp, "risk_level", "UNKNOWN") or "UNKNOWN",
            risk_label_es=risk_label_es(getattr(opp, "risk_level", None) or "UNKNOWN"),
            strengths=opp_strengths,
            weaknesses=opp_weaknesses,
        )

    # --- NegotiationResult ---
    neg = getattr(result, "negotiation", None)
    negotiation_schema: NegotiationResultSchema | None = None
    if neg is not None:
        # NegotiationArguments
        args = getattr(neg, "negotiation_arguments", []) or []
        arg_schemas = [
            NegotiationArgumentSchema(
                argument=getattr(a, "argument", ""),
                economic_impact=getattr(a, "economic_impact", 0.0) or 0.0,
                category=getattr(a, "category", "defect") or "defect",
                severity=getattr(a, "severity", 5) or 5,
            )
            for a in args
        ]

        # NegotiationScript
        script = getattr(neg, "negotiation_script", None)
        script_schema: NegotiationScriptSchema | None = None
        if script is not None:
            script_schema = NegotiationScriptSchema(
                opening=getattr(script, "opening", "") or "",
                defect_based_points=getattr(script, "defect_based_points", []) or [],
                market_based_points=getattr(script, "market_based_points", []) or [],
                closing=getattr(script, "closing", "") or "",
            )

        rec = getattr(neg, "recommendation", None)
        rec_str = rec.value if hasattr(rec, "value") else str(rec or "WALK_AWAY")

        negotiation_schema = NegotiationResultSchema(
            estimated_vehicle_value=getattr(neg, "estimated_vehicle_value", 0.0) or 0.0,
            recommended_initial_offer=getattr(neg, "recommended_initial_offer", 0.0) or 0.0,
            recommended_counter_offer=getattr(neg, "recommended_counter_offer", 0.0) or 0.0,
            maximum_purchase_price=getattr(neg, "maximum_purchase_price", 0.0) or 0.0,
            walk_away_price=getattr(neg, "walk_away_price", 0.0) or 0.0,
            expected_profit=getattr(neg, "expected_profit", 0.0) or 0.0,
            expected_roi=getattr(neg, "expected_roi", 0.0) or 0.0,
            negotiation_arguments=arg_schemas,
            negotiation_script=script_schema or NegotiationScriptSchema(),
            recommendation=rec_str,
            leverage_score=getattr(neg, "leverage_score", 50.0) or 50.0,
            price_gap=getattr(neg, "price_gap", 0.0) or 0.0,
            discount_needed=getattr(neg, "discount_needed", 0.0) or 0.0,
        )

    # --- Construir item ---
    return SearchResultItem(
        source=getattr(vehicle, "source", None),
        external_id=getattr(vehicle, "external_id", None),
        url=getattr(vehicle, "url", None),
        brand=getattr(vehicle, "brand", None),
        model=getattr(vehicle, "model", None),
        year=getattr(vehicle, "year", None),
        mileage=getattr(vehicle, "mileage", None),
        fuel_type=getattr(vehicle, "fuel_type", None),
        transmission=getattr(vehicle, "transmission", None),
        power_hp=getattr(vehicle, "power_hp", None),
        price=getattr(vehicle, "price", None),
        currency=getattr(vehicle, "currency", None),
        location=getattr(vehicle, "location", None),
        images=images,
        description=getattr(vehicle, "description", None),
        vehicle_score=vehicle_score_schema,
        market_estimation=market_estimation_schema,
        profit_analysis=profit_analysis_schema,
        opportunity=opportunity_schema,
        negotiation=negotiation_schema,
    )


@router.post(
    "/search",
    response_model=SearchAPIResponse,
    status_code=status.HTTP_200_OK,
    summary="Buscar vehículos",
    description="Ejecuta una búsqueda completa de vehículos a través de los "
    "proveedores especificados. Incluye scoring, análisis de mercado, "
    "rentabilidad y detección de oportunidades.",
    responses={
        200: {
            "description": "Búsqueda completada con éxito",
            "model": SearchAPIResponse,
        },
        400: {
            "description": "Error de validación en la petición",
        },
        422: {
            "description": "Error de validación Pydantic",
        },
        500: {
            "description": "Error interno del servidor",
        },
    },
)
async def search_vehicles(
    request: SearchAPIRequest,
    search_engine: SearchEngineService = Depends(get_search_engine_service),
    current_user: User = Depends(require_search),
) -> SearchAPIResponse:
    """Ejecuta una búsqueda completa de vehículos.

    Convierte la petición API a SearchRequest interno y serializa
    los resultados del dominio a schemas estables de la API.
    """
    # Convertir API request → domain SearchRequest
    domain_request = request.to_search_request()

    # TASK-007: métricas de negocio (cada provider solicitado cuenta una petición)
    for provider in domain_request.providers:
        record_search_request(provider)

    # Ejecutar búsqueda (pipeline completo)
    engine_result = await search_engine.search(domain_request)

    # Convertir resultados internos → API responses
    items = [_build_search_result_item(r) for r in engine_result.results]
    summary = engine_result.summary

    # TASK-007: oportunidades detectadas en este resultado
    for item in items:
        if item.opportunity is not None:
            record_opportunity_generated()

    # TASK-008: Alerta operativa si todas las fuentes solicitadas fallaron
    provider_issues_list = getattr(engine_result, "provider_issues", []) or []
    if provider_issues_list:
        import logging
        logger_ops = logging.getLogger("app.api.search_ops")
        requested_providers = set(domain_request.providers)
        failed_providers = {issue.provider for issue in provider_issues_list if getattr(issue, "stage", "") == "search"}
        if requested_providers and requested_providers.issubset(failed_providers):
            logger_ops.warning(
                "SEARCH_API_ALERT: All requested providers %s failed. Potential proxy block, cookie expiration, or anti-bot activation.",
                requested_providers,
            )

    return SearchAPIResponse(
        summary=SearchSummarySchema(
            total_results=summary.total_results,
            excellent=summary.excellent,
            good=summary.good,
            average=summary.average,
            poor=summary.poor,
            rejected=summary.rejected,
        ),
        results=items,
        # SEARCH.DIAG.1: providers caídos, con mensaje ES para la UI.
        provider_issues=[
            ProviderIssueSchema(**payload)
            for payload in build_provider_issue_payloads(
                getattr(engine_result, "provider_issues", [])
            )
        ],
    )

