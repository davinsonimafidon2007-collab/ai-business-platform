"""add confidence column to opportunities

Revision ID: u7v8w9x0y1z2
Revises: r4s5t6u7v8w9
Create Date: 2026-09-03 00:00:00.000000

TASK 2: separa explícitamente profitability (profit/roi ya existentes) de
confidence (fiabilidad de los datos usados). Ver app/services/confidence.py.
Nullable porque las oportunidades ya existentes no tienen este dato
calculado retroactivamente; se recalcula cuando corre RefreshOpportunityJob.

Re-encadenada al fusionar con origin/main (auditoría/hardening en
paralelo): origin/main ya había creado su propia
q3r4s5t6u7v8_add_opportunity_phases_table.py + r4s5t6u7v8w9x0_data_layer_
hardening.py + r4s5t6u7v8w9_deal_state_machine_v2.py con esos mismos
revision ids (colisión real de nombres, no solo de contenido). Esta
migración pasa a encadenar después de deal_state_machine_v2 con un id
nuevo sin colisión.
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "u7v8w9x0y1z2"
down_revision = "r4s5t6u7v8w9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "opportunities",
        sa.Column("confidence", sa.Float(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("opportunities", "confidence")
