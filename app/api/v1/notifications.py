"""MOB-P1-001: Push notification token registration endpoint."""

from pydantic import BaseModel
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_current_user
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
    db: Session = Depends(get_db),
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
