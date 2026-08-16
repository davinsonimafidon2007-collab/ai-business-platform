from __future__ import annotations

import pytest

from app.models.role import Role
from app.services.permission_service import PermissionService


@pytest.fixture
def permission_service() -> PermissionService:
    return PermissionService()


class TestPermissionService:
    def test_admin_can_search(self, permission_service: PermissionService) -> None:
        assert permission_service.can_search(Role.ADMIN) is True

    def test_admin_can_manage_users(self, permission_service: PermissionService) -> None:
        assert permission_service.can_manage_users(Role.ADMIN) is True

    def test_admin_can_manage_api_keys(self, permission_service: PermissionService) -> None:
        assert permission_service.can_manage_api_keys(Role.ADMIN) is True

    def test_admin_can_view_admin(self, permission_service: PermissionService) -> None:
        assert permission_service.can_view_admin(Role.ADMIN) is True

    def test_admin_can_view_audit_logs(self, permission_service: PermissionService) -> None:
        assert permission_service.can_view_audit_logs(Role.ADMIN) is True

    def test_user_can_search(self, permission_service: PermissionService) -> None:
        assert permission_service.can_search(Role.USER) is True

    def test_user_can_manage_own_api_keys(self, permission_service: PermissionService) -> None:
        assert permission_service.can_manage_own_api_keys(Role.USER) is True

    def test_user_cannot_manage_users(self, permission_service: PermissionService) -> None:
        assert permission_service.can_manage_users(Role.USER) is False

    def test_user_cannot_view_admin(self, permission_service: PermissionService) -> None:
        assert permission_service.can_view_admin(Role.USER) is False

    def test_user_cannot_view_audit_logs(self, permission_service: PermissionService) -> None:
        assert permission_service.can_view_audit_logs(Role.USER) is False

    def test_admin_has_all_permissions(self, permission_service: PermissionService) -> None:
        permissions = permission_service.get_permissions(Role.ADMIN)
        expected = {
            "search",
            "manage_users",
            "manage_api_keys",
            "view_admin",
            "manage_roles",
            "view_audit_logs",
        }
        assert permissions == expected

    def test_user_has_correct_permissions(self, permission_service: PermissionService) -> None:
        permissions = permission_service.get_permissions(Role.USER)
        expected = {
            "search",
            "manage_own_api_keys",
        }
        assert permissions == expected

    def test_can_method_works_for_valid_permission(self, permission_service: PermissionService) -> None:
        assert permission_service.can(Role.ADMIN, "search") is True
        assert permission_service.can(Role.USER, "search") is True

    def test_can_method_works_for_invalid_permission(self, permission_service: PermissionService) -> None:
        assert permission_service.can(Role.ADMIN, "nonexistent_permission") is False
        assert permission_service.can(Role.USER, "nonexistent_permission") is False
