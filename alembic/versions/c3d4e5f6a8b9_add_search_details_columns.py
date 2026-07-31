"""add query, results_count, execution_time to searches

Revision ID: c3d4e5f6a8b9
Revises: b2c3d4e5f6a8
Create Date: 2026-08-01 10:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "c3d4e5f6a8b9"
down_revision = "b2c3d4e5f6a8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("searches", sa.Column("query", sa.String(length=500), nullable=True))
    op.add_column("searches", sa.Column("results_count", sa.Integer(), nullable=True))
    op.add_column("searches", sa.Column("execution_time", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("searches", "execution_time")
    op.drop_column("searches", "results_count")
    op.drop_column("searches", "query")