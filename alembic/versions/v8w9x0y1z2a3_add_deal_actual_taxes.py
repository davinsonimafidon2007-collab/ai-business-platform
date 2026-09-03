"""add actual_taxes to deals (business lifecycle reporting)

Revision ID: v8w9x0y1z2a3
Revises: t6u7v8w9x0y1
Create Date: 2026-09-03 00:00:00.000000

Separa los impuestos reales pagados (IEDMT + IVA en matriculación) del
coste administrativo de matriculación (``registration_cost``), igual que
ProfitAnalyzer._compute_cost_breakdown ya trata ``taxes`` y
``registration_cost`` como líneas distintas en el lado previsto. Sin esto,
no había forma de comparar impuesto previsto vs. impuesto real pagado por
operación (reporting de cartera / TASK "lifecycle de negocio completo").
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "v8w9x0y1z2a3"
down_revision = "t6u7v8w9x0y1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "deals",
        sa.Column("actual_taxes", sa.Numeric(12, 2), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("deals", "actual_taxes")
