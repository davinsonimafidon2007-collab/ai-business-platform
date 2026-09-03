from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    # SEC.INPUT.1: tope superior para no procesar contraseñas gigantes.
    password: str = Field(..., min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)


class GoogleAuthRequest(BaseModel):
    # SEC.INPUT.1: un id_token JWT real nunca supera ~4 KB.
    id_token: str = Field(..., max_length=4096)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
