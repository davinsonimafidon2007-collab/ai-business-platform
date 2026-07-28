"""API v1 router.

Aggregates all route modules into a single APIRouter.
This is the only entry point that `main.py` needs to include.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.routes.health import router as health_router
from app.api.v1.routes.inspection import router as inspection_router
from app.api.v1.routes.search import router as search_router
from app.api.v1.routes.vehicles import router as vehicles_router

api_router = APIRouter()

# Include all route modules
api_router.include_router(health_router)
api_router.include_router(inspection_router)
api_router.include_router(search_router)
api_router.include_router(vehicles_router)
api_router.include_router(dashboard_router)

__all__ = ["api_router"]

