"""add feature_flags table

Revision ID: n5o6p7q8r9s0
Revises: m3n4o5p6q7r8
Create Date: 2026-08-14

TASK-012: tabla de feature flags con toggles que el admin puede cambiar
sin reiniciar la API. El cache L1 vive en Redis (TTL 60s) y la DB es la
fuente de verdad.
"""

from alembic import op
import sqlalchemy as sa


revision = "n5o6p7q8r9s0"
down_revision = "m3n4o5p6q7r8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "feature_flags",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("key", sa.String(100), nullable=False),
        sa.Column("value", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_feature_flags_key"), "feature_flags", ["key"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_feature_flags_key"), table_name="feature_flags")
    op.drop_table("feature_flags")