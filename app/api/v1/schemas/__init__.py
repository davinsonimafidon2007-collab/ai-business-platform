"""API v1 Pydantic schemas for the REST layer.

These schemas are STABLE API contracts decoupled from internal dataclasses.
Internal domain models (VehicleScore, ProfitAnalysis, etc.) are converted
to these schemas before being returned as JSON responses.
"""

from app.api.v1.schemas.common import (
    CostBreakdownSchema,
    MarketEstimationSchema,
    OpportunityAnalysisSchema,
    ProfitAnalysisSchema,
    VehicleScoreSchema,
)
from app.api.v1.schemas.health import HealthResponse
from app.api.v1.schemas.search import (
    SearchAPIRequest,
    SearchAPIResponse,
    SearchResultItem,
    SearchSummarySchema,
)
from app.api.v1.schemas.vehicle import (
    ProviderListResponse,
    VehicleDetailResponse,
)

__all__ = [
    "HealthResponse",
    "VehicleScoreSchema",
    "MarketEstimationSchema",
    "CostBreakdownSchema",
    "ProfitAnalysisSchema",
    "OpportunityAnalysisSchema",
    "SearchAPIRequest",
    "SearchSummarySchema",
    "SearchResultItem",
    "SearchAPIResponse",
    "VehicleDetailResponse",
    "ProviderListResponse",
]

