from __future__ import annotations

from app.models.role import Role

# ── Role-based permission definitions ──────────────────────────────────────
# Granular permissions are defined as a simple dict-based system.
# This avoids creating a separate Permission model while still providing
# fine-grained access control.

ROLE_PERMISSIONS: dict[Role, set[str]] = {
    Role.ADMIN: {
        "search",
        "manage_users",
        "manage_api_keys",
        "view_admin",
        "manage_roles",
        "view_audit_logs",
    },
    Role.USER: {
        "search",
        "manage_own_api_keys",
    },
}


class PermissionService:
    """Simple dict-based permission service.

    Permissions are checked against a predefined dictionary mapping roles
    to their allowed permissions. No database model is needed.
    """

    def can(self, role: Role, permission: str) -> bool:
        """Check if a role has a specific permission."""
        permissions = ROLE_PERMISSIONS.get(role, set())
        return permission in permissions

    def can_search(self, role: Role) -> bool:
        return self.can(role, "search")

    def can_manage_users(self, role: Role) -> bool:
        return self.can(role, "manage_users")

    def can_manage_api_keys(self, role: Role) -> bool:
        return self.can(role, "manage_api_keys")

    def can_manage_own_api_keys(self, role: Role) -> bool:
        return self.can(role, "manage_own_api_keys")

    def can_view_admin(self, role: Role) -> bool:
        return self.can(role, "view_admin")

    def can_view_audit_logs(self, role: Role) -> bool:
        return self.can(role, "view_audit_logs")

    def get_permissions(self, role: Role) -> set[str]:
        """Get all permissions for a role."""
        return ROLE_PERMISSIONS.get(role, set())
