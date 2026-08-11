"""Legacy cleanup: harden nullable user_id fields.

Revision ID: j2k3l4m5n6o7
Revises: i1j2k3l4m5n6
Create Date: 2026-08-10
"""

from alembic import op
import sqlalchemy as sa

revision = "j2k3l4m5n6o7"
down_revision = "i1j2k3l4m5n6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Delete orphan rows with NULL user_id in searches (legacy pre-migration)
    op.execute("DELETE FROM searches WHERE user_id IS NULL")

    # Harden searches.user_id to NOT NULL
    op.alter_column(
        "searches",
        "user_id",
        existing_type=sa.String(36),
        nullable=False,
    )

    # search_history: keep nullable (SET NULL on user delete is intentional)
    # but add an index for query performance. e7f8a9b0c1d2 ya creó
    # ix_search_history_user_id; la guardamos aquí para que la cadena sea
    # idempotente en BD que ya tienen el índice (evita DuplicateTableError).
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_search_history_user_id
        ON search_history (user_id)
        """
    )


def downgrade() -> None:
    op.drop_index("ix_search_history_user_id", table_name="search_history")
    op.alter_column(
        "searches",
        "user_id",
        existing_type=sa.String(36),
        nullable=True,
    )
