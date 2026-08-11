"""Pydantic schemas for the Inspection Session API.

These are the request/response models for the inspection endpoints.
They do NOT duplicate existing DTOs from app/models/negotiation.py.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

# =============================================================================
# Request schemas
# =============================================================================


class InspectionSessionCreate(BaseModel):
    """Request to create a new inspection session."""

    vehicle_id: str = Field(..., description="ID of the vehicle to inspect")


class ObservationUpdate(BaseModel):
    """Request to update an inspection observation."""

    category_id: str = Field(..., description="Category ID (e.g. 'exterior')")
    item_id: str = Field(..., description="Item ID (e.g. 'pintura')")
    status: str = Field(
        ..., description="Status: GOOD, WARNING, BAD, or UNKNOWN"
    )
    notes: str | None = Field(None, description="Optional inspector notes")
    estimated_repair_cost: float | None = Field(
        None, description="Estimated repair cost in EUR", ge=0
    )


class PhotoUploadRequest(BaseModel):
    """Request to upload a photo for an observation."""

    observation_id: str = Field(..., description="ID of the observation")
    file_path: str = Field(..., description="Path or URL of the photo file")
    file_name: str | None = Field(None, description="Original file name")
    mime_type: str | None = Field(None, description="MIME type")
    file_size_bytes: int | None = Field(
        None, description="File size in bytes", ge=0
    )


class VisionAnalyzeRequest(BaseModel):
    """Optional subset of a session's uploaded photographs to analyze."""

    photo_ids: list[str] | None = None


# =============================================================================
# Response schemas
# =============================================================================


class ObservationResponse(BaseModel):
    """Response model for an inspection observation."""

    id: str
    session_id: str
    category_id: str
    item_id: str
    status: str
    notes: str | None = None
    estimated_repair_cost: float | None = None
    severity: str
    created_at: str | None = None
    updated_at: str | None = None


class PhotoResponse(BaseModel):
    """Response model for an inspection photo."""

    id: str
    observation_id: str
    session_id: str
    file_path: str
    file_name: str | None = None
    mime_type: str | None = None
    file_size_bytes: int | None = None
    ai_analysis_status: str = "PENDING"
    created_at: str | None = None


class VisionSuggestionResponse(BaseModel):
    photo_id: str
    observation_id: str
    category_id: str
    item_id: str
    status: str
    severity: str
    confidence: str
    notes: str
    suggested_repair_cost: float | None = None


class VisionAnalysisResponse(BaseModel):
    summary: str
    suggestions: list[VisionSuggestionResponse] = []
    # GRAVE.006: identifica el backend de vision usado. `simulated=True`
    # significa que el análisis es un Mock local (observaciones inventadas) y
    # la UI debe avisarlo para no tomar decisiones de negocio sobre datos falsos.
    provider: str = "mock"
    simulated: bool = True


class CatalogItemResponse(BaseModel):
    """A single item in the inspection catalog with its current status."""

    id: str
    label: str
    description: str = ""
    order: int = 0
    is_safety_relevant: bool = False
    has_cost_estimate: bool = True
    allows_photos: bool = True
    status: str = "UNKNOWN"
    notes: str | None = None
    estimated_repair_cost: float | None = None
    severity: str = "LOW"
    observation_id: str | None = None


class CatalogCategoryResponse(BaseModel):
    """A category in the inspection catalog with its items."""

    id: str
    label: str
    icon: str = "📋"
    description: str = ""
    order: int = 0
    items: list[CatalogItemResponse] = []


class InspectionSessionResponse(BaseModel):
    """Response model for an inspection session."""

    id: str
    vehicle_id: str
    status: str
    current_category_order: int = 1
    total_repair_cost: float = 0.0
    total_defects: int = 0
    total_critical_defects: int = 0
    risk_level: str | None = None
    recommendation: str | None = None
    overall_condition: int | None = None
    notes: str | None = None
    summary: dict[str, Any] | None = None
    created_at: str | None = None
    updated_at: str | None = None
    completed_at: str | None = None


class InspectionSessionDetailResponse(BaseModel):
    """Detailed response with session, observations, photos, and catalog."""

    session: InspectionSessionResponse
    observations: list[ObservationResponse] = []
    photos: list[PhotoResponse] = []
    catalog: list[CatalogCategoryResponse] = []


class InspectionSummaryResponse(BaseModel):
    """Response model for the inspection summary."""

    session_id: str
    vehicle_id: str
    status: str
    progress: dict[str, Any] = {}
    defects: dict[str, Any] = {}
    costs: dict[str, Any] = {}
    overall_condition: int | None = None
    risk_level: str = "NONE"
    recommendation: str = ""
    defect_items: list[dict[str, Any]] = []
    repair_estimate: dict[str, Any] = {}
    inspection_result: dict[str, Any] = {}
    negotiation: dict[str, Any] | None = None
