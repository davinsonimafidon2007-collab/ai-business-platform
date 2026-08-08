"""E2E.MANUAL.PASS.1: el email del usuario local debe pasar EmailStr.

Bug detectado en el run manual: ``LOCAL_USER_EMAIL`` era "local@localhost" y
``UserRead`` usa ``EmailStr``, así que ``GET /api/v1/auth/me`` devolvía 500 con
AUTH_DISABLED=true. El segundo intento ("local@localhost.local") también falló:
``.local`` es un TLD reservado que email-validator rechaza.
"""

from __future__ import annotations

import pytest
from pydantic import BaseModel, EmailStr, ValidationError

from app.core.local_user import (
    LOCAL_USER_EMAIL,
    LOCAL_USER_ID,
    LOCAL_USER_ID_STR,
)


class _EmailProbe(BaseModel):
    """Mismo contrato que UserRead.email."""

    email: EmailStr


def test_local_user_email_is_valid_for_emailstr() -> None:
    """El email local debe validar: si no, /auth/me responde 500."""
    assert _EmailProbe(email=LOCAL_USER_EMAIL).email == LOCAL_USER_EMAIL


@pytest.mark.parametrize("bad_email", ["local@localhost", "local@localhost.local"])
def test_previously_broken_emails_are_still_rejected(bad_email: str) -> None:
    """Regresión: documenta por qué no se puede volver a esos valores."""
    with pytest.raises(ValidationError):
        _EmailProbe(email=bad_email)


def test_local_user_uuid_is_stable() -> None:
    """El UUID no debe cambiar: rompería las FKs de datos ya guardados."""
    assert LOCAL_USER_ID_STR == "00000000-0000-4000-8000-000000000001"
    assert str(LOCAL_USER_ID) == LOCAL_USER_ID_STR
