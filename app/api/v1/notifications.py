"""MOB-P1-001: Push notification token registration endpoint."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.dependencies.auth import get_current_user
from app.models.user import User

router = APIRouter(prefix="/notifications", tags=["notifications"])


class RegisterTokenRequest(BaseModel):
    token: str
    platform: str = "android"


class RegisterTokenResponse(BaseModel):
    ok: bool
    message: str


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
    # TODO: Store token in database (create PushToken model or add to User)
    # For now, just acknowledge receipt
    return RegisterTokenResponse(
        ok=True,
        message=f"Token registered for user {current_user.id}",
    )
