"""API v1 router.

Aggregates all route modules into a single APIRouter.
This is the only entry point that `main.py` needs to include.
"""

from __future__ import annotations

from fastapi import APIRouter

# Import route modules
from app.api.v1.admin_api_keys import router as admin_api_keys_router
from app.api.v1.admin_feature_flags import router as admin_feature_flags_router
from app.api.v1.admin_metrics import router as admin_metrics_router
from app.api.v1.admin_status import router as admin_status_router
from app.api.v1.api_keys import router as api_keys_router
from app.api.v1.auth import router as auth_router
from app.api.v1.budget_search import router as budget_search_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.deals import router as deals_router
from app.api.v1.notifications import router as notifications_router
from app.api.v1.opportunities import router as opportunities_router
from app.api.v1.routes.health import router as health_router
from app.api.v1.routes.inspection import router as inspection_router
from app.api.v1.routes.search import router as search_router
from app.api.v1.routes.vehicles import router as vehicles_provider_router
from app.api.v1.search_orders import router as search_orders_router
from app.api.v1.searches import router as searches_router
from app.api.v1.users import router as users_router
from app.api.v1.vehicles import router as vehicles_crud_router

api_router = APIRouter()

# Include all route modules (without any duplication)
api_router.include_router(auth_router)
api_router.include_router(api_keys_router)
api_router.include_router(admin_api_keys_router)
api_router.include_router(admin_feature_flags_router)
api_router.include_router(admin_metrics_router)
api_router.include_router(admin_status_router)
api_router.include_router(dashboard_router)
api_router.include_router(searches_router)
api_router.include_router(search_orders_router)
api_router.include_router(users_router)
api_router.include_router(vehicles_crud_router)
api_router.include_router(health_router)
api_router.include_router(inspection_router)
api_router.include_router(search_router)
api_router.include_router(vehicles_provider_router)
api_router.include_router(opportunities_router)
api_router.include_router(deals_router)
api_router.include_router(budget_search_router)
api_router.include_router(notifications_router)

__all__ = ["api_router"]
