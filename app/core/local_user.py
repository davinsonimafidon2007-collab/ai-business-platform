"""Usuario sintético cuando AUTH_DISABLED=true (uso personal/local).

Estos valores son fijos y documentados (nunca aleatorios por request) para que
las FKs de vehicles/deals/searches/etc. apunten siempre al mismo ``users`` row.
"""

from __future__ import annotations

from uuid import UUID

# UUID fijo documentado para el usuario local ADMIN.
LOCAL_USER_ID = UUID("00000000-0000-4000-8000-000000000001")
LOCAL_USER_ID_STR = str(LOCAL_USER_ID)
# UserRead usa EmailStr: "local@localhost" no valida (sin TLD) y ".local" es
# un TLD reservado que email-validator también rechaza — ambos daban 500 en
# /auth/me (E2E.MANUAL.PASS.1). "example.com" está reservado por la RFC 2606
# justo para esto y nunca resolverá a un buzón real.
# El UUID NO se toca: cambiarlo rompería las FKs ya guardadas.
LOCAL_USER_EMAIL = "local@example.com"
LOCAL_USER_FULL_NAME = "Local Admin"
