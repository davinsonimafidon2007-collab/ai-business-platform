"""Per-user unique on vehicles (user_id, source, external_id)

Revision ID: l2m3n4o5p6q7
Revises: k3l4m5n6o7p8
Create Date: 2026-08-11

GRAVE.007: el unique global (source, external_id) impide que dos usuarios
guarden el mismo anuncio. Lo sustituimos por un unique por usuario.
MED.009: el modelo SQLAlchemy pasa a declarar este constraint en __table_args__.
"""

from __future__ import annotations

from alembic import op


revision = "l2m3n4o5p6q7"
down_revision = "k3l4m5n6o7p8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Quitar el unique global (source, external_id)
    op.drop_index(op.f("ix_vehicles_source_external_id"), table_name="vehicles")
    # Unique por usuario: cada usuario guarda un anuncio como máximo una vez
    op.create_index(
        "ix_vehicles_user_source_external",
        "vehicles",
        ["user_id", "source", "external_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_vehicles_user_source_external", table_name="vehicles")
    op.create_index(
        op.f("ix_vehicles_source_external_id"),
        "vehicles",
        ["source", "external_id"],
        unique=True,
    )
