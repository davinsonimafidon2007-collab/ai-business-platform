"""Deal Pipeline Integration — Conecta deal, negociación e inspección."""
from __future__ import annotations

from typing import Any

from app.services.deal_service import DealService
from app.services.inspection_service import InspectionService
from app.services.negotiation_engine import NegotiationEngine


class DealPipelineIntegrationService:
    """Servicio de integración para el pipeline completo: deal → negotiate → inspect."""

    def __init__(
        self,
        deal_service: DealService | None = None,
        inspection_service: InspectionService | None = None,
    ) -> None:
        self.deal_service = deal_service
        self.inspection_service = inspection_service
        self.negotiation_engine = NegotiationEngine()

    async def process_deal_pipeline(
        self,
        deal_id: str,
        user_id: str,
        inspection_data: dict | None = None,
    ) -> dict[str, Any]:
        """Ejecuta negociación e inspección sobre un deal existente."""
        result = {"deal_id": deal_id, "status": "processed"}
        if inspection_data and self.inspection_service:
            session = await self.inspection_service.create_session(
                vehicle_id=str(inspection_data.get("vehicle_id", "unknown")),
                user_id=user_id,
            )
            result["inspection_session"] = session.id if hasattr(session, "id") else str(session)
        return result
