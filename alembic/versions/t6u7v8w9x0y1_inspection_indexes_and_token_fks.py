"""TASK 9: indexes on inspection tables + real FKs on token/audit user_id

Revision ID: t6u7v8w9x0y1
Revises: s5t6u7v8w9x0
Create Date: 2026-09-03 00:00:00.000000

AUD-017: ninguna tabla de inspección tenía índice en sus FKs.
InspectionObservationRepository.get_by_session y
InspectionPhotoRepository.get_by_session/get_by_observation escaneaban la
tabla entera.

AUD-018: password_reset_tokens.user_id, verification_tokens.user_id y
audit_logs.user_id eran varchar(36) sin FK — una referencia lógica no
forzada por la BD, y de tipo incompatible con users.id (uuid nativo). Mismo
patrón que el equipo ya aplicó a api_keys/refresh_tokens en f8a9b0c1d2e3:
1) borrar filas huérfanas, 2) castear el tipo, 3) crear la FK.

audit_logs.resource_id NO lleva FK: es deliberadamente polimórfico (según
`resource` puede referenciar vehicles/opportunities/deals/...), no apunta a
una única tabla.
"""

from __future__ import annotations

from alembic import op


revision = "t6u7v8w9x0y1"
down_revision = "s5t6u7v8w9x0"
branch_labels = None
depends_on = None

_TOKEN_TABLES_CASCADE = ("password_reset_tokens", "verification_tokens")


def upgrade() -> None:
    # --- Índices en las tablas de inspección ---
    op.create_index(
        op.f("ix_inspection_sessions_vehicle_id"),
        "inspection_sessions",
        ["vehicle_id"],
    )
    op.create_index(
        op.f("ix_inspection_sessions_user_id"),
        "inspection_sessions",
        ["user_id"],
    )
    op.create_index(
        op.f("ix_inspection_observations_session_id"),
        "inspection_observations",
        ["session_id"],
    )
    op.create_index(
        op.f("ix_inspection_photos_observation_id"),
        "inspection_photos",
        ["observation_id"],
    )
    op.create_index(
        op.f("ix_inspection_photos_session_id"),
        "inspection_photos",
        ["session_id"],
    )

    # --- FK real en password_reset_tokens.user_id / verification_tokens.user_id ---
    for table in _TOKEN_TABLES_CASCADE:
        op.execute(
            f"DELETE FROM {table} t "
            "WHERE t.user_id IS NOT NULL "
            f"AND NOT EXISTS (SELECT 1 FROM users u WHERE u.id::text = t.user_id)"
        )
        op.execute(
            f"ALTER TABLE {table} ALTER COLUMN user_id TYPE uuid USING user_id::uuid"
        )
        op.create_foreign_key(
            f"fk_{table}_user_id_users",
            table,
            "users",
            ["user_id"],
            ["id"],
            ondelete="CASCADE",
        )

    # --- FK real en audit_logs.user_id (nullable, SET NULL: el historial de
    # auditoría sobrevive al borrado del usuario, solo se desvincula) ---
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
    op.execute("ALTER TABLE audit_logs ALTER COLUMN user_id TYPE varchar(36) USING user_id::text")

    for table in reversed(_TOKEN_TABLES_CASCADE):
        op.drop_constraint(f"fk_{table}_user_id_users", table, type_="foreignkey")
        op.execute(
            f"ALTER TABLE {table} ALTER COLUMN user_id TYPE varchar(36) USING user_id::text"
        )

    op.drop_index(
        op.f("ix_inspection_photos_session_id"), table_name="inspection_photos"
    )
    op.drop_index(
        op.f("ix_inspection_photos_observation_id"), table_name="inspection_photos"
    )
    op.drop_index(
        op.f("ix_inspection_observations_session_id"),
        table_name="inspection_observations",
    )
    op.drop_index(
        op.f("ix_inspection_sessions_user_id"), table_name="inspection_sessions"
    )
    op.drop_index(
        op.f("ix_inspection_sessions_vehicle_id"), table_name="inspection_sessions"
    )
