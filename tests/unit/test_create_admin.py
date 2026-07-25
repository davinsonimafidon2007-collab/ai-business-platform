from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from app.models.role import Role
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.scripts.create_admin import create_admin_user
from app.services.auth_service import AuthService, password_hasher
from app.services.user_service import UserService


@pytest.mark.asyncio
async def test_create_admin_user_successfully():
    """Verifica que se crea un usuario administrador correctamente."""
    mock_session = AsyncMock()
    repository = UserRepository(mock_session)

    email = "admin@example.com"
    password = "SecurePass123!"

    # Mock de get_by_email para que no exista el usuario
    repository.get_by_email = AsyncMock(return_value=None)
    
    # Mock de create_user
    admin_user = User(email=email, hashed_password=password_hasher.hash(password), full_name="Administrator")
    repository.create = AsyncMock(return_value=admin_user)
    repository.update = AsyncMock(return_value=admin_user)

    # Ejecutar con sesión mock
    await create_admin_user(email, password, session=mock_session)

    # Verificar que se llamó a create
    repository.create.assert_called_once()
    created_user = repository.create.call_args[0][0]
    assert created_user.email == email
    assert created_user.role == Role.USER  # Inicialmente USER
    
    # Verificar que se actualizó a ADMIN
    repository.update.assert_called_once()
    updated_user = repository.update.call_args[0][0]
    assert updated_user.role == Role.ADMIN


@pytest.mark.asyncio
async def test_create_admin_user_raises_when_user_exists():
    """Verifica que no se crea el admin si el usuario ya existe."""
    mock_session = AsyncMock()
    repository = UserRepository(mock_session)

    email = "existing@example.com"
    existing_user = User(email=email, hashed_password="hashed", role=Role.USER)
    repository.get_by_email = AsyncMock(return_value=existing_user)

    with pytest.raises(SystemExit):
        await create_admin_user(email, "password123", session=mock_session)


@pytest.mark.asyncio
async def test_create_admin_user_validates_password_length():
    """Verifica que se valida la longitud mínima de la contraseña."""
    with pytest.raises(SystemExit):
        await create_admin_user("admin@example.com", "short")


@pytest.mark.asyncio
async def test_create_admin_user_rejects_common_passwords():
    """Verifica que se rechazan contraseñas comunes."""
    common_passwords = ["password", "12345678", "admin123", "changeme"]
    
    for common_password in common_passwords:
        with pytest.raises(SystemExit):
            await create_admin_user("admin@example.com", common_password)


@pytest.mark.asyncio
async def test_create_admin_user_hashes_password():
    """Verifica que la contraseña se hashea correctamente."""
    mock_session = AsyncMock()
    repository = UserRepository(mock_session)

    email = "admin@example.com"
    password = "SecurePass123!"

    repository.get_by_email = AsyncMock(return_value=None)
    
    admin_user = User(email=email, hashed_password="hashed", full_name="Administrator")
    repository.create = AsyncMock(return_value=admin_user)
    repository.update = AsyncMock(return_value=admin_user)

    await create_admin_user(email, password, session=mock_session)

    # Verificar que se hasheó la contraseña
    created_user = repository.create.call_args[0][0]
    assert created_user.hashed_password != password
    assert created_user.hashed_password.startswith("$")  # Formato Argon2


@pytest.mark.asyncio
async def test_create_admin_user_sets_correct_role():
    """Verifica que el usuario se crea con rol ADMIN."""
    mock_session = AsyncMock()
    repository = UserRepository(mock_session)

    email = "admin@example.com"
    password = "SecurePass123!"

    repository.get_by_email = AsyncMock(return_value=None)
    
    admin_user = User(email=email, hashed_password=password_hasher.hash(password), full_name="Administrator")
    repository.create = AsyncMock(return_value=admin_user)
    
    updated_admin = User(email=email, hashed_password=password_hasher.hash(password), full_name="Administrator", role=Role.ADMIN)
    repository.update = AsyncMock(return_value=updated_admin)

    await create_admin_user(email, password, session=mock_session)

    # Verificar que se actualizó el rol a ADMIN
    updated_user = repository.update.call_args[0][0]
    assert updated_user.role == Role.ADMIN
