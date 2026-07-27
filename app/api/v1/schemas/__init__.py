"""API v1 Pydantic schemas for the REST layer.

These schemas are STABLE API contracts decoupled from internal dataclasses.
Internal domain models (VehicleScore, ProfitAnalysis, etc.) are converted
to these schemas before being returned as JSON responses.
"""

from app.api.v1.schemas.health import HealthResponse
from app.api.v1.schemas.common import (
    VehicleScoreSchema,
    MarketEstimationSchema,
    CostBreakdownSchema,
    ProfitAnalysisSchema,
    OpportunityAnalysisSchema,
)
from app.api.v1.schemas.search import (
    SearchAPIRequest,
    SearchSummarySchema,
    SearchResultItem,
    SearchAPIResponse,
)
from app.api.v1.schemas.vehicle import (
    VehicleDetailResponse,
    ProviderListResponse,
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

