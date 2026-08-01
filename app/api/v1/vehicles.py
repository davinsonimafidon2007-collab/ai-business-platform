from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.models.vehicle import Vehicle
from app.repositories.vehicle_evaluation_repository import VehicleEvaluationRepository
from app.repositories.vehicle_repository import VehicleRepository
from app.schemas.vehicle import VehicleCreate, VehicleRead, VehicleUpdate
from app.schemas.vehicle_evaluation import VehicleEvaluationRead, VehicleEvaluationUpdate
from app.services.vehicle_evaluation_service import VehicleEvaluationService
from app.services.vehicle_service import VehicleService

router = APIRouter(prefix="/vehicles", tags=["Vehicles"])


async def get_vehicle_service(session: AsyncSession = Depends(get_db_session)) -> VehicleService:
    repository = VehicleRepository(session)
    return VehicleService(repository)


async def get_vehicle_evaluation_service(session: AsyncSession = Depends(get_db_session)) -> VehicleEvaluationService:
    repository = VehicleEvaluationRepository(session)
    return VehicleEvaluationService(repository)


async def _get_owned_vehicle(vehicle_id: str, current_user: User, service: VehicleService) -> Vehicle:
    vehicle = await service.get_vehicle(vehicle_id)
    if vehicle is None or vehicle.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")
    return vehicle


@router.post("", response_model=VehicleRead, status_code=status.HTTP_201_CREATED)
async def create_vehicle(
    payload: VehicleCreate,
    service: VehicleService = Depends(get_vehicle_service),
    current_user: User = Depends(get_current_user),
) -> VehicleRead:
    data = payload.model_dump()
    data["user_id"] = current_user.id
    vehicle = await service.create_vehicle(data)
    return VehicleRead.model_validate(vehicle)


@router.get("", response_model=list[VehicleRead])
async def list_vehicles(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    service: VehicleService = Depends(get_vehicle_service),
    current_user: User = Depends(get_current_user),
) -> list[VehicleRead]:
    vehicles = await service.list_vehicles_by_user(current_user.id, skip=skip, limit=limit)
    return [VehicleRead.model_validate(v) for v in vehicles]


@router.get("/{vehicle_id}", response_model=VehicleRead)
async def get_vehicle(
    vehicle_id: str,
    service: VehicleService = Depends(get_vehicle_service),
    current_user: User = Depends(get_current_user),
) -> VehicleRead:
    vehicle = await _get_owned_vehicle(vehicle_id, current_user, service)
    return VehicleRead.model_validate(vehicle)


@router.patch("/{vehicle_id}", response_model=VehicleRead)
async def update_vehicle(
    vehicle_id: str,
    payload: VehicleUpdate,
    service: VehicleService = Depends(get_vehicle_service),
    current_user: User = Depends(get_current_user),
) -> VehicleRead:
    vehicle = await _get_owned_vehicle(vehicle_id, current_user, service)
    updated = await service.update_vehicle(vehicle, payload.model_dump(exclude_unset=True))
    return VehicleRead.model_validate(updated)


@router.delete("/{vehicle_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vehicle(
    vehicle_id: str,
    service: VehicleService = Depends(get_vehicle_service),
    current_user: User = Depends(get_current_user),
) -> None:
    vehicle = await _get_owned_vehicle(vehicle_id, current_user, service)
    await service.delete_vehicle(vehicle)


# ---------------------------------------------------------------------------
# Vehicle Evaluations (sub-resource of vehicles)
# ---------------------------------------------------------------------------


@router.post("/{vehicle_id}/evaluation", response_model=VehicleEvaluationRead, status_code=status.HTTP_201_CREATED)
async def create_vehicle_evaluation(
    vehicle_id: str,
    vehicle_service: VehicleService = Depends(get_vehicle_service),
    evaluation_service: VehicleEvaluationService = Depends(get_vehicle_evaluation_service),
    current_user: User = Depends(get_current_user),
) -> VehicleEvaluationRead:
    """Calcula (o recalcula) la evaluación real del vehículo con EvaluationEngine.

    No acepta valores del cliente: todos los campos se calculan en el servidor
    a partir de los datos del vehículo, para evitar que se puedan falsear.
    """
    vehicle = await _get_owned_vehicle(vehicle_id, current_user, vehicle_service)
    evaluation = await evaluation_service.evaluate_vehicle(vehicle)
    return VehicleEvaluationRead.model_validate(evaluation)


@router.get("/{vehicle_id}/evaluation", response_model=VehicleEvaluationRead)
async def get_vehicle_evaluation(
    vehicle_id: str,
    vehicle_service: VehicleService = Depends(get_vehicle_service),
    evaluation_service: VehicleEvaluationService = Depends(get_vehicle_evaluation_service),
    current_user: User = Depends(get_current_user),
) -> VehicleEvaluationRead:
    await _get_owned_vehicle(vehicle_id, current_user, vehicle_service)
    evaluation = await evaluation_service.get_evaluation_by_vehicle(vehicle_id)
    if evaluation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evaluation not found")
    return VehicleEvaluationRead.model_validate(evaluation)


@router.patch("/{vehicle_id}/evaluation", response_model=VehicleEvaluationRead)
async def update_vehicle_evaluation(
    vehicle_id: str,
    payload: VehicleEvaluationUpdate,
    vehicle_service: VehicleService = Depends(get_vehicle_service),
    evaluation_service: VehicleEvaluationService = Depends(get_vehicle_evaluation_service),
    current_user: User = Depends(get_current_user),
) -> VehicleEvaluationRead:
    await _get_owned_vehicle(vehicle_id, current_user, vehicle_service)
    evaluation = await evaluation_service.get_evaluation_by_vehicle(vehicle_id)
    if evaluation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evaluation not found")
    updated = await evaluation_service.update_evaluation(evaluation, payload.model_dump(exclude_unset=True))
    return VehicleEvaluationRead.model_validate(updated)


@router.delete("/{vehicle_id}/evaluation", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vehicle_evaluation(
    vehicle_id: str,
    vehicle_service: VehicleService = Depends(get_vehicle_service),
    evaluation_service: VehicleEvaluationService = Depends(get_vehicle_evaluation_service),
    current_user: User = Depends(get_current_user),
) -> None:
    await _get_owned_vehicle(vehicle_id, current_user, vehicle_service)
    evaluation = await evaluation_service.get_evaluation_by_vehicle(vehicle_id)
    if evaluation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evaluation not found")
    await evaluation_service.delete_evaluation(evaluation)