"""add search_orders.attempts

Revision ID: i1j2k3l4m5n6
Revises: h2i3j4k5l6m7
Create Date: 2026-08-10 00:00:00.000000

Contador de intentos de procesamiento por orden (J1): una orden FAILED se
reintenta solo mientras ``attempts < search_order_max_attempts`` y respetando
el cooldown; al superar el tope se abandona en vez de reintentarse cada ciclo
del scheduler (ruido, carga y posible rate-limit del provider).
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "i1j2k3l4m5n6"
down_revision = "h2i3j4k5l6m7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "search_orders",
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("search_orders", "attempts")
