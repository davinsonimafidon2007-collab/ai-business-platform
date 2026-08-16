"""Business metrics endpoint — TASK-007 (FASE 8).

Expone las métricas de negocio en formato Prometheus text/plain
(https://prometheus.io/docs/instrumenting/exposition_formats/).
Protegido por ``require_admin``.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse

from app.dependencies.auth import require_admin
from app.models.user import User
from app.services.metrics_service import metrics

router = APIRouter(prefix="/admin/metrics", tags=["admin-metrics"])


@router.get("", response_class=PlainTextResponse)
async def get_metrics(
    _: User = Depends(require_admin),
) -> str:
    return metrics.to_prometheus()