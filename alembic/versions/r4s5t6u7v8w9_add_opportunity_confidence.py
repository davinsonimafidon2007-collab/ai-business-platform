"""add confidence column to opportunities

Revision ID: r4s5t6u7v8w9
Revises: q3r4s5t6u7v8
Create Date: 2026-09-03 00:00:00.000000

TASK 2: separa explícitamente profitability (profit/roi ya existentes) de
confidence (fiabilidad de los datos usados). Ver app/services/confidence.py.
Nullable porque las oportunidades ya existentes no tienen este dato
calculado retroactivamente; se recalcula cuando corre RefreshOpportunityJob.
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "r4s5t6u7v8w9"
down_revision = "q3r4s5t6u7v8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "opportunities",
        sa.Column("confidence", sa.Float(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("opportunities", "confidence")
