"""vehicles.user_id NOT NULL + indexes on user_id columns

Revision ID: d6e7f8a9b0c1
Revises: c3d4e5f6a8b9
Create Date: 2026-08-02 00:00:00.000000

Alinea la DB con el modelo SQLAlchemy (Vehicle.user_id nullable=False)
y añade índices para consultas de ownership.
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "d6e7f8a9b0c1"
down_revision = "c3d4e5f6a8b9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1) Eliminar vehículos huérfanos (sin dueño). Tras ownership obligatorio
    #    no deben existir filas con user_id NULL.
    op.execute("DELETE FROM vehicles WHERE user_id IS NULL")

    # 2) vehicles.user_id → NOT NULL (alineado con app/models/vehicle.py)
    op.alter_column(
        "vehicles",
        "user_id",
        existing_type=sa.Uuid(as_uuid=False),
        nullable=False,
    )

    # 3) Índices de ownership (consultas list_by_user, IDOR checks)
    op.create_index(
        op.f("ix_vehicles_user_id"),
        "vehicles",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_searches_user_id"),
        "searches",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_searches_user_id"), table_name="searches")
    op.drop_index(op.f("ix_vehicles_user_id"), table_name="vehicles")
    op.alter_column(
        "vehicles",
        "user_id",
        existing_type=sa.Uuid(as_uuid=False),
        nullable=True,
    )
