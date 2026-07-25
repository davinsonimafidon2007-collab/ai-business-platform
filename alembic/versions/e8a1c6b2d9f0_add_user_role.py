"""add user role

Revision ID: e8a1c6b2d9f0
Revises: d4ff07bc4343
Create Date: 2026-07-25 06:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "e8a1c6b2d9f0"
down_revision = "d4ff07bc4343"
branch_labels = None
depends_on = None

role_enum = sa.Enum("admin", "user", name="role")


def upgrade() -> None:
    role_enum.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "users",
        sa.Column("role", role_enum, nullable=False, server_default=sa.text("'user'")),
    )
    op.alter_column("users", "role", server_default=None)


def downgrade() -> None:
    op.drop_column("users", "role")
    role_enum.drop(op.get_bind(), checkfirst=True)
