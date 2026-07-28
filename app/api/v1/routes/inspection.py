"""REST API endpoints for the Inspection Session module.

All business logic is delegated to InspectionService.
These endpoints only handle HTTP concerns (parsing, validation, response).
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.v1.dependencies import get_inspection_service
from app.api.v1.schemas.inspection import (
    InspectionSessionCreate,
    InspectionSessionDetailResponse,
    InspectionSessionResponse,
    InspectionSummaryResponse,
    ObservationResponse,
    ObservationUpdate,
    PhotoResponse,
    PhotoUploadRequest,
    VisionAnalysisResponse,
    VisionAnalyzeRequest,
)
from app.services.inspection_service import InspectionService

router = APIRouter(prefix="/inspections", tags=["inspections"])


@router.post(
    "",
    response_model=InspectionSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new inspection session",
)
async def create_session(
    data: InspectionSessionCreate,
    service: InspectionService = Depends(get_inspection_service),
) -> InspectionSessionResponse:
    """Creates a new inspection session for a vehicle."""
    session = await service.create_session(data.vehicle_id)
    return InspectionSessionResponse(**session.to_dict())


@router.get(
    "/{session_id}",
    response_model=InspectionSessionDetailResponse,
    summary="Get inspection session details",
)
async def get_session(
    session_id: str,
    service: InspectionService = Depends(get_inspection_service),
) -> InspectionSessionDetailResponse:
    """Gets a session with all observations, photos, and catalog."""
    result = await service.get_session_with_details(session_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inspection session '{session_id}' not found",
        )
    return InspectionSessionDetailResponse(**result)


@router.put(
    "/{session_id}/items",
    response_model=ObservationResponse,
    summary="Create or update an inspection observation",
)
async def update_item(
    session_id: str,
    data: ObservationUpdate,
    service: InspectionService = Depends(get_inspection_service),
) -> ObservationResponse:
    """Creates or updates an observation for a catalog item."""
    try:
        observation = await service.update_item(
            session_id=session_id,
            category_id=data.category_id,
            item_id=data.item_id,
            status=data.status,
            notes=data.notes,
            estimated_repair_cost=data.estimated_repair_cost,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    return ObservationResponse(**observation.to_dict())


@router.post(
    "/{session_id}/photos",
    response_model=PhotoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a photo for an observation",
)
async def upload_photo(
    session_id: str,
    data: PhotoUploadRequest,
    service: InspectionService = Depends(get_inspection_service),
) -> PhotoResponse:
    """Registers a photo associated with an observation."""
    photo = await service.upload_photo(
        session_id=session_id,
        observation_id=data.observation_id,
        file_path=data.file_path,
        file_name=data.file_name,
        mime_type=data.mime_type,
        file_size_bytes=data.file_size_bytes,
    )
    return PhotoResponse(**photo.to_dict())


@router.post(
    "/{session_id}/analyze",
    response_model=VisionAnalysisResponse,
    summary="Analyze inspection photographs and return suggestions",
)
async def analyze_photos(
    session_id: str,
    data: VisionAnalyzeRequest,
    service: InspectionService = Depends(get_inspection_service),
) -> VisionAnalysisResponse:
    """Analyzes photos but never applies suggested inspection changes."""
    try:
        result = await service.analyze_photos(session_id, data.photo_ids)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return VisionAnalysisResponse(**result)


@router.post(
    "/{session_id}/finalize",
    response_model=InspectionSessionResponse,
    summary="Finalize an inspection session",
)
async def finalize_session(
    session_id: str,
    service: InspectionService = Depends(get_inspection_service),
) -> InspectionSessionResponse:
    """Finalizes a session, generates summary, and marks as COMPLETED."""
    try:
        session = await service.finalize_session(session_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    return InspectionSessionResponse(**session.to_dict())


@router.get(
    "/{session_id}/summary",
    response_model=InspectionSummaryResponse,
    summary="Get inspection summary",
)
async def get_summary(
    session_id: str,
    service: InspectionService = Depends(get_inspection_service),
) -> InspectionSummaryResponse:
    """Gets the inspection summary (partial or complete)."""
    summary = await service.generate_summary(session_id)
    if summary is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inspection session '{session_id}' not found",
        )
    return InspectionSummaryResponse(**summary)
