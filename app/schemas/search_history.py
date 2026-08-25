from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SearchHistoryRead(BaseModel):
    """Schema de lectura para el historial de búsquedas."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str | None = None
    query: str
    timestamp: datetime
    providers_used: str | None = None
    results_count: int | None = None
    execution_time: float | None = None