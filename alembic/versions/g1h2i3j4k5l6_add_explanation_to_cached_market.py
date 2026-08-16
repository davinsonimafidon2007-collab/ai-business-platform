"""add explanation to cached_market_data

Revision ID: g1h2i3j4k5l6
Revises: f2a3b4c5d6e8
Create Date: 2026-08-06 00:00:00.000000

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "g1h2i3j4k5l6"
down_revision = "f2a3b4c5d6e8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "cached_market_data",
        sa.Column("explanation", sa.Text, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("cached_market_data", "explanation")
