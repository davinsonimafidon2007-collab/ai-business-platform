from __future__ import annotations

from pydantic import BaseModel


class VerificationRequestResponse(BaseModel):
    message: str = "Verification email sent"


class VerifyRequest(BaseModel):
    token: str


class VerifyResponse(BaseModel):
    message: str = "Email verified successfully"