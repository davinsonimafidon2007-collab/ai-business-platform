"""Prometheus scrape endpoint (public) — Bloque 6 / DEVOPS.

Expone las métricas de negocio en formato Prometheus text/plain
(https://prometheus.io/docs/instrumenting/exposition_formats/) SIN
autenticación para que Prometheus pueda hacer ``scrape`` desde la red
interna de docker (perfil ``obs``).

Seguridad: este endpoint es de solo lectura (métricas agregadas, no datos
de usuario). En un despliegue público se debe restringir el acceso por red
(firewall / red interna docker), igual que ``/health``.
"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

from app.services.metrics_service import metrics

router = APIRouter(tags=["metrics"])


@router.get("/metrics", response_class=PlainTextResponse)
async def get_prometheus_metrics() -> str:
    """Métricas de negocio en formato Prometheus (sin auth, scraping interno)."""
    return metrics.to_prometheus()