"""Vehicle and provider endpoints.

GET /vehicle/{provider}/{id} — Obtiene detalle de un vehículo desde un provider.
GET /providers — Lista todos los proveedores registrados.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.api.v1.dependencies import get_provider
from app.api.v1.schemas.vehicle import ProviderListResponse, VehicleDetailResponse
from app.providers.dto import VehicleDetail
from app.providers.registry import ProviderRegistry

router = APIRouter(tags=["Vehicles"])


def _build_vehicle_detail_response(detail: VehicleDetail) -> VehicleDetailResponse:
    """Convierte un VehicleDetail interno en VehicleDetailResponse de la API."""
    return VehicleDetailResponse(
        source=detail.source,
        external_id=detail.external_id,
        url=detail.url,
        brand=detail.brand,
        model=detail.model,
        category=detail.category,
        version=detail.version,
        year=detail.year,
        mileage=detail.mileage,
        fuel_type=detail.fuel_type,
        transmission=detail.transmission,
        power_hp=detail.power_hp,
        displacement_cc=detail.displacement_cc,
        doors=detail.doors,
        color=detail.color,
        emissions=detail.emissions,
        location=detail.location,
        seller_type=detail.seller_type,
        first_registration=detail.first_registration,
        price=detail.price,
        currency=detail.currency,
        vin=detail.vin,
        description=detail.description,
        images=detail.images or [],
        equipment=detail.equipment or [],
    )


@router.get(
    "/vehicle/{provider}/{id}",
    response_model=VehicleDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Obtener detalle de un vehículo",
    description="Obtiene la información detallada de un vehículo desde el "
    "proveedor especificado.",
    responses={
        200: {
            "description": "Detalle del vehículo obtenido con éxito",
            "model": VehicleDetailResponse,
        },
        404: {
            "description": "Proveedor o vehículo no encontrado",
        },
        500: {
            "description": "Error al consultar el proveedor",
        },
    },
)
async def get_vehicle_detail(
    provider: str,
    id: str,
) -> VehicleDetailResponse:
    """Obtiene el detalle de un vehículo desde un proveedor.

    Usa get_provider() desde dependencies.py para resolver el provider
    por nombre (levanta HTTPException 404 si no existe).

    Args:
        provider: Nombre del proveedor (mobile_de, autoscout24).
        id: ID externo del vehículo en el proveedor.

    Returns:
        VehicleDetailResponse con la información completa del vehículo.
    """
    # Resolver provider mediante DI (valida existencia y levanta 404 si no existe)
    prov = get_provider(provider)

    try:
        detail: VehicleDetail = await prov.get_vehicle(id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching vehicle from provider '{provider}': {str(e)}",
        )

    if detail is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vehicle with id '{id}' not found in provider '{provider}'",
        )

    return _build_vehicle_detail_response(detail)


@router.get(
    "/providers",
    response_model=ProviderListResponse,
    status_code=status.HTTP_200_OK,
    summary="Listar proveedores registrados",
    description="Devuelve la lista de todos los proveedores de vehículos "
    "registrados en el sistema.",
    responses={
        200: {
            "description": "Lista de proveedores obtenida con éxito",
            "model": ProviderListResponse,
        },
    },
)
def list_providers() -> ProviderListResponse:
    """Lista todos los proveedores registrados."""
    return ProviderListResponse(providers=ProviderRegistry.list_providers())

