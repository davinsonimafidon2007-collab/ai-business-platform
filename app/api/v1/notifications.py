"""MOB-P1-001: Push notification token registration endpoint."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.repositories.push_token_repository import PushTokenRepository

router = APIRouter(prefix="/notifications", tags=["notifications"])


class RegisterTokenRequest(BaseModel):
    token: str
    platform: str = "android"


class RegisterTokenResponse(BaseModel):
    ok: bool
    message: str


class SendPushRequest(BaseModel):
    title: str
    body: str
    data: dict | None = None


class SendPushResponse(BaseModel):
    ok: bool
    result: dict


@router.post("/register", response_model=RegisterTokenResponse)
async def register_push_token(
    body: RegisterTokenRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> RegisterTokenResponse:
    """Register a push notification token (FCM) for the current user.

    Stores the token so the backend can send push notifications
    (e.g., new opportunities, deal updates) to this device.
    """
    repo = PushTokenRepository(db)
    await repo.upsert(user_id=current_user.id, token=body.token, platform=body.platform)
    return RegisterTokenResponse(
        ok=True,
        message=f"Token registered for user {current_user.id}",
    )


@router.post("/unregister", response_model=RegisterTokenResponse)
async def unregister_push_token(
    body: RegisterTokenRequest,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> RegisterTokenResponse:
    """Remove a previously registered push notification token (FCM).

    Called on logout so the backend stops sending push notifications
    to a device that no longer belongs to a signed-in session.
    """
    repo = PushTokenRepository(db)
    await repo.delete_by_token(token=body.token)
    return RegisterTokenResponse(
        ok=True,
        message="Token unregistered",
    )


@router.post("/send", response_model=SendPushResponse)
async def send_push_notification(
    body: SendPushRequest,
    current_user: User = Depends(get_current_user),
) -> SendPushResponse:
    """Send a test push notification to the current user (FCM).

    TASK-010 (FASE 5): permite verificar de forma manual el envío FCM a los
    tokens registrados del usuario autenticado. Sin Firebase configurado el
    servicio responde ``skipped=True`` (dry-run, patrón del proyecto).
    """
    from app.services.push_service import PushNotificationService

    result = await PushNotificationService.send_to_user(
        user_id=str(current_user.id),
        title=body.title,
        body=body.body,
        data=body.data,
    )
    return SendPushResponse(ok=True, result=result)
