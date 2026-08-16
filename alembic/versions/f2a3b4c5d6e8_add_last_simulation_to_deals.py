"""add last simulation fields to deals

Revision ID: f2a3b4c5d6e8
Revises: e2f3a4b5c6d7
Create Date: 2026-08-04 00:00:00.000000

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "f2a3b4c5d6e8"
down_revision = "e2f3a4b5c6d7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Añade los campos de la última simulación de margen a deals (Task E.2)."""
    op.add_column(
        "deals",
        sa.Column("last_sim_purchase_price", sa.Numeric(12, 2), nullable=True),
    )
    op.add_column(
        "deals",
        sa.Column("last_sim_sale_price", sa.Numeric(12, 2), nullable=True),
    )
    op.add_column(
        "deals",
        sa.Column("last_sim_total_cost", sa.Numeric(12, 2), nullable=True),
    )
    op.add_column(
        "deals",
        sa.Column("last_sim_net_profit", sa.Numeric(12, 2), nullable=True),
    )
    op.add_column(
        "deals",
        sa.Column("last_sim_roi", sa.Numeric(12, 2), nullable=True),
    )
    op.add_column(
        "deals",
        sa.Column("last_sim_profile", sa.String(20), nullable=True),
    )
    op.add_column(
        "deals",
        sa.Column("last_sim_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    """Revoca los campos de la última simulación."""
    op.drop_column("deals", "last_sim_at")
    op.drop_column("deals", "last_sim_profile")
    op.drop_column("deals", "last_sim_roi")
    op.drop_column("deals", "last_sim_net_profit")
    op.drop_column("deals", "last_sim_total_cost")
    op.drop_column("deals", "last_sim_sale_price")
    op.drop_column("deals", "last_sim_purchase_price")
