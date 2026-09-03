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
    if vehicle is None:
        # Support lookups by external_id from provider results.
        if data.external_id:
            vehicle = await vehicle_repo.get_by_external_id(
                source=data.source or "",
                external_id=data.external_id,
                user_id=str(current_user.id),
            )
        if vehicle is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Vehicle '{data.vehicle_id}' not found",
            )
    if vehicle.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vehicle '{data.vehicle_id}' not found",
        )
    session = await service.create_session(vehicle.id, current_user.id)
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

# Firmas de fichero (magic bytes) de los formatos de imagen aceptados.
# TASK 8 (AUD-024): el `content_type` y la extensión los controla el cliente;
# lo único no falsificable es el contenido.
_IMAGE_SIGNATURES: tuple[tuple[bytes, str], ...] = (
    (b"\xff\xd8\xff", ".jpg"),          # JPEG
    (b"\x89PNG\r\n\x1a\n", ".png"),     # PNG
    (b"GIF87a", ".gif"),                # GIF
    (b"GIF89a", ".gif"),                # GIF
)
_UPLOAD_CHUNK_SIZE = 64 * 1024


def _detect_image_extension(content: bytes) -> str | None:
    """Extensión segura deducida del contenido real, o None si no es imagen."""
    for signature, extension in _IMAGE_SIGNATURES:
        if content.startswith(signature):
            return extension
    # Formatos basados en contenedor RIFF/ISO-BMFF: la marca está desplazada.
    if len(content) >= 12:
        if content[:4] == b"RIFF" and content[8:12] == b"WEBP":
            return ".webp"
        if content[4:8] == b"ftyp" and content[8:12] in (
            b"heic",
            b"heix",
            b"hevc",
            b"mif1",
        ):
            return ".heic"
    return None


async def _read_upload_within_limit(file: UploadFile) -> bytes:
    """Lee la subida en trozos, abortando si supera el tamaño máximo.

    Devuelve el contenido completo si cabe en el límite; si no, lanza 413 sin
    haber materializado el fichero entero en memoria.
    """
    max_bytes = max(1, int(settings.max_upload_size_mb)) * 1024 * 1024
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(_UPLOAD_CHUNK_SIZE)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail=(
                    f"El fichero supera el máximo permitido de "
                    f"{settings.max_upload_size_mb} MB."
                ),
            )
        chunks.append(chunk)
    if total == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El fichero está vacío.",
        )
    return b"".join(chunks)


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

    # Validate declared content type (barato, pero falsificable por el
    # cliente: la comprobación real es la de magic bytes de más abajo).
    if file.content_type and not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File must be an image, got {file.content_type}",
        )

    # TASK 8 (AUD-024): lectura en trozos con tope de tamaño. Antes se hacía
    # `await file.read()` sin límite: un solo fichero grande podía agotar la
    # memoria del proceso.
    content = await _read_upload_within_limit(file)

    # TASK 8 (AUD-024): validación real por magic bytes. El content_type y la
    # extensión los elige el cliente; esto comprueba el contenido de verdad.
    detected_ext = _detect_image_extension(content)
    if detected_ext is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "El contenido del fichero no es una imagen reconocible "
                "(se aceptan JPEG, PNG, WebP, GIF y HEIC)."
            ),
        )

    # Create upload directory
    session_dir = UPLOAD_DIR / session_id
    session_dir.mkdir(parents=True, exist_ok=True)

    # Nombre generado + extensión DETECTADA (no la que envía el cliente).
    unique_name = f"{uuid.uuid4()}{detected_ext}"
    file_path = session_dir / unique_name

    # Save file
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