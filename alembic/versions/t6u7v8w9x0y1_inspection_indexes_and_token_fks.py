"""TASK 9: real FK on audit_logs.user_id

Revision ID: t6u7v8w9x0y1
Revises: s5t6u7v8w9x0
Create Date: 2026-09-03 00:00:00.000000

AUD-018: audit_logs.user_id era varchar(36) sin FK — una referencia lógica
no forzada por la BD, y de tipo incompatible con users.id (uuid nativo).

Recortada al fusionar con origin/main (auditoría/hardening en paralelo):
origin/main ya cubrió, en r4s5t6u7v8w9x0_data_layer_hardening.py, los
índices de las tablas de inspección (vehicle_id/user_id/created_at en
sessions, session_id en observations, observation_id/session_id en
photos) y las FKs de password_reset_tokens.user_id/verification_tokens.
user_id con CASCADE. Lo único que quedaba sin cubrir era audit_logs.
user_id, que esta migración añade con SET NULL (no CASCADE): borrar un
usuario no debe borrar su historial de auditoría, solo desvincularlo.

audit_logs.resource_id NO lleva FK: es deliberadamente polimórfico (según
`resource` puede referenciar vehicles/opportunities/deals/...), no apunta
a una única tabla.
"""

from __future__ import annotations

from alembic import op


revision = "t6u7v8w9x0y1"
down_revision = "s5t6u7v8w9x0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "UPDATE audit_logs SET user_id = NULL "
        "WHERE user_id IS NOT NULL "
        "AND NOT EXISTS (SELECT 1 FROM users u WHERE u.id::text = audit_logs.user_id)"
    )
    op.execute(
        "ALTER TABLE audit_logs ALTER COLUMN user_id TYPE uuid USING user_id::uuid"
    )
    op.create_foreign_key(
        "fk_audit_logs_user_id_users",
        "audit_logs",
        "users",
        ["user_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_audit_logs_user_id_users", "audit_logs", type_="foreignkey")
    op.execute(
        "ALTER TABLE audit_logs ALTER COLUMN user_id TYPE varchar(36) USING user_id::text"
    )
