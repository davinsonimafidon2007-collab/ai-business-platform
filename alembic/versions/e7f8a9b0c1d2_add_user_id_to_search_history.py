"""add user_id to search_history

Revision ID: e7f8a9b0c1d2
Revises: d6e7f8a9b0c1
Create Date: 2026-08-02 00:00:00.000000

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "e7f8a9b0c1d2"
down_revision = "d6e7f8a9b0c1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "search_history",
        sa.Column("user_id", sa.Uuid(as_uuid=False), nullable=True),
    )
    op.create_index(
        op.f("ix_search_history_user_id"),
        "search_history",
        ["user_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_search_history_user_id_users",
        "search_history",
        "users",
        ["user_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_search_history_user_id_users", "search_history", type_="foreignkey")
    op.drop_index(op.f("ix_search_history_user_id"), table_name="search_history")
    op.drop_column("search_history", "user_id")
