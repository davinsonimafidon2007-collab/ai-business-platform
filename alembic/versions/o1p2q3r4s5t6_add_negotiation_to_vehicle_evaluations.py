"""add negotiation column to vehicle_evaluations

Revision ID: o1p2q3r4s5t6
Revises: n5o6p7q8r9s0
Create Date: 2026-08-18

INTEGRATION.WEB.1: el modelo VehicleEvaluation declara ``negotiation``
(JSON Text) pero la migración c1d2e3f4a5b6 que creó la tabla no incluía la
columna. Sin esta migración, el job de órdenes de búsqueda (background)
fallaba persistiendo evaluaciones: ''column vehicle_evaluations.negotiation
does not exist''.
"""

from alembic import op
import sqlalchemy as sa


revision = "o1p2q3r4s5t6"
down_revision = "n5o6p7q8r9s0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "vehicle_evaluations",
        sa.Column("negotiation", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("vehicle_evaluations", "negotiation")