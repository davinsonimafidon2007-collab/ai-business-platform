"""REST API endpoints for the Inspection Session module.

All business logic is delegated to InspectionService.
These endpoints only handle HTTP concerns (parsing, validation, response).
"""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

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
from app.core.config import settings
from app.database import get_db_session
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.repositories.vehicle_repository import VehicleRepository
from app.services.inspection_service import InspectionService

router = APIRouter(prefix="/inspections", tags=["inspections"])


async def get_vehicle_repository(session: AsyncSession = Depends(get_db_session)) -> VehicleRepository:
    return VehicleRepository(session)


async def _get_owned_session(
    session_id: str,
    current_user: User,
    service: InspectionService,
):
    """Obtiene la sesión y verifica que pertenece al usuario actual.

    Devuelve 404 tanto si no existe como si pertenece a otro usuario,
    para no filtrar la existencia de sesiones ajenas.
    """
    session = await service.get_session(session_id)
    if session is None or session.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inspection session '{session_id}' not found",
        )
    return session


@router.post(
    "",
    response_model=InspectionSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new inspection session",
)
async def create_session(
    data: InspectionSessionCreate,
    current_user: User = Depends(get_current_user),
    service: InspectionService = Depends(get_inspection_service),
    vehicle_repo: VehicleRepository = Depends(get_vehicle_repository),
) -> InspectionSessionResponse:
    """Creates a new inspection session for a vehicle."""
    vehicle = await vehicle_repo.get_by_id(data.vehicle_id)
    if vehicle is None or vehicle.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vehicle '{data.vehicle_id}' not found",
        )
    session = await service.create_session(data.vehicle_id, current_user.id)
    return InspectionSessionResponse(**session.to_dict())


@router.get(
    "/{session_id}",
    response_model=InspectionSessionDetailResponse,
    summary="Get inspection session details",
)
async def get_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    service: InspectionService = Depends(get_inspection_service),
) -> InspectionSessionDetailResponse:
    """Gets a session with all observations, photos, and catalog."""
    await _get_owned_session(session_id, current_user, service)
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
    current_user: User = Depends(get_current_user),
    service: InspectionService = Depends(get_inspection_service),
) -> ObservationResponse:
    """Creates or updates an observation for a catalog item."""
    await _get_owned_session(session_id, current_user, service)
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
        ) from e
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
    current_user: User = Depends(get_current_user),
    service: InspectionService = Depends(get_inspection_service),
) -> PhotoResponse:
    """Registers a photo associated with an observation."""
    await _get_owned_session(session_id, current_user, service)
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
    current_user: User = Depends(get_current_user),
    service: InspectionService = Depends(get_inspection_service),
) -> VisionAnalysisResponse:
    """Analyzes photos but never applies suggested inspection changes."""
    await _get_owned_session(session_id, current_user, service)
    try:
        result = await service.analyze_photos(session_id, data.photo_ids)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    return VisionAnalysisResponse(**result)


@router.post(
    "/{session_id}/finalize",
    response_model=InspectionSessionResponse,
    summary="Finalize an inspection session",
)
async def finalize_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    service: InspectionService = Depends(get_inspection_service),
) -> InspectionSessionResponse:
    """Finalizes a session, generates summary, and marks as COMPLETED."""
    await _get_owned_session(session_id, current_user, service)
    try:
        session = await service.finalize_session(session_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    return InspectionSessionResponse(**session.to_dict())


@router.get(
    "/{session_id}/summary",
    response_model=InspectionSummaryResponse,
    summary="Get inspection summary",
)
async def get_summary(
    session_id: str,
    current_user: User = Depends(get_current_user),
    service: InspectionService = Depends(get_inspection_service),
) -> InspectionSummaryResponse:
    """Gets the inspection summary (partial or complete)."""
    await _get_owned_session(session_id, current_user, service)
    summary = await service.generate_summary(session_id)
    if summary is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inspection session '{session_id}' not found",
        )
    return InspectionSummaryResponse(**summary)


UPLOAD_DIR = Path(settings.upload_dir)


@router.post(
    "/{session_id}/photos/upload",
    status_code=status.HTTP_201_CREATED,
    summary="Upload a photo file for an inspection observation",
)
async def upload_photo_file(
    session_id: str,
    observation_id: str,
    file: UploadFile,
    service: InspectionService = Depends(get_inspection_service),
    current_user: User = Depends(get_current_user),
) -> PhotoResponse:
    """Receives a multipart image file, saves it, and registers it.

    - observation_id is passed as query param (?observation_id=...)
    - The file is saved to the configured UPLOAD_DIR
    - Returns the created InspectionPhoto record
    """
    # Validate session exists and belongs to the current user
    await _get_owned_session(session_id, current_user, service)

    # Validate file is an image
    if file.content_type and not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File must be an image, got {file.content_type}",
        )

    # Create upload directory
    session_dir = UPLOAD_DIR / session_id
    session_dir.mkdir(parents=True, exist_ok=True)

    # Generate unique filename
    ext = Path(file.filename or "photo.jpg").suffix or ".jpg"
    unique_name = f"{uuid.uuid4()}{ext}"
    file_path = session_dir / unique_name

    # Save file
    content = await file.read()
    file_path.write_bytes(content)

    # Register in database
    photo = await service.upload_photo(
        session_id=session_id,
        observation_id=observation_id,
        file_path=str(file_path),
        file_name=file.filename,
        mime_type=file.content_type,
        file_size_bytes=len(content),
    )
    return PhotoResponse(**photo.to_dict())