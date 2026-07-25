"""Script para crear el primer usuario administrador.

Uso:
    uv run python -m app.scripts.create_admin

Este script solicita interactivamente el email y password del administrador,
y crea el usuario con rol ADMIN en la base de datos.
"""

from __future__ import annotations

import asyncio
import getpass
import sys

from app.core.config import settings
from app.db.session import get_db_session
from app.models.role import Role
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService, password_hasher
from app.services.user_service import UserService


async def create_admin_user(email: str, password: str, session=None) -> None:
    """Crea un usuario administrador en la base de datos.
    
    Args:
        email: Email del administrador.
        password: Contraseña del administrador.
        session: Sesión de base de datos opcional (para tests).
        
    Raises:
        SystemExit: Si el usuario ya existe o hay un error.
    """
    # Validar longitud de password
    if len(password) < 8:
        print("❌ Error: La contraseña debe tener al menos 8 caracteres.")
        sys.exit(1)

    # Validar que no sea una contraseña común
    if password in {"password", "12345678", "admin123", "changeme"}:
        print("❌ Error: La contraseña es demasiado común. Por favor, elige una más segura.")
        sys.exit(1)

    # Usar sesión proporcionada o crear una nueva
    if session is not None:
        repository = UserRepository(session)
        await _create_admin_with_repository(email, password, repository)
    else:
        async with get_db_session() as db_session:
            repository = UserRepository(db_session)
            await _create_admin_with_repository(email, password, repository)


async def _create_admin_with_repository(email: str, password: str, repository: UserRepository) -> None:
    """Lógica interna para crear admin con un repositorio dado."""
    auth_service = AuthService(repository)
    user_service = UserService(repository)

    # Verificar si el usuario ya existe
    existing_user = await repository.get_by_email(email)
    if existing_user is not None:
        print(f"❌ Error: Ya existe un usuario con el email '{email}'.")
        sys.exit(1)

    # Crear el usuario administrador
    try:
        hashed_password = password_hasher.hash(password)
        admin_user = await user_service.create_user(
            email=email,
            hashed_password=hashed_password,
            full_name="Administrator",
        )
        
        # Actualizar el rol a ADMIN
        admin_user.role = Role.ADMIN
        await repository.update(admin_user)
        
        print(f"✅ Usuario administrador creado exitosamente:")
        print(f"   Email: {admin_user.email}")
        print(f"   ID: {admin_user.id}")
        print(f"   Rol: {admin_user.role.value}")
        print()
        print("⚠️  IMPORTANTE: Guarda estas credenciales en un lugar seguro.")
        print("   Por favor, cambia la contraseña después del primer inicio de sesión.")
        
    except Exception as exc:
        print(f"❌ Error al crear el usuario administrador: {exc}")
        sys.exit(1)


def main() -> None:
    """Función principal del script."""
    print("=" * 60)
    print("Creación de Usuario Administrador")
    print("=" * 60)
    print()
    print("Este script creará el primer usuario administrador del sistema.")
    print("Por favor, proporciona las credenciales del administrador.")
    print()

    # Solicitar email
    email = input("Email del administrador: ").strip()
    if not email or "@" not in email:
        print("❌ Error: Debes proporcionar un email válido.")
        sys.exit(1)

    # Solicitar password (oculto en consola)
    password = getpass.getpass("Contraseña del administrador: ")
    if not password:
        print("❌ Error: Debes proporcionar una contraseña.")
        sys.exit(1)

    # Confirmar password
    password_confirm = getpass.getpass("Confirma la contraseña: ")
    if password != password_confirm:
        print("❌ Error: Las contraseñas no coinciden.")
        sys.exit(1)

    print()
    print("Creando usuario administrador...")
    print()

    # Ejecutar la creación del usuario
    asyncio.run(create_admin_user(email, password))


if __name__ == "__main__":
    main()