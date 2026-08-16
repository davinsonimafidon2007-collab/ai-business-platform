"""add verification_tokens table and is_verified to users

Revision ID: a8b2c3d4e5f6
Revises: 6c96678f4c71
Create Date: 2026-07-25 22:40:00.000000

"""

from alembic import op
import sqlalchemy as sa


revision = "a8b2c3d4e5f6"
down_revision = "6c96678f4c71"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add is_verified column to users table
    op.add_column(
        "users",
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.alter_column("users", "is_verified", server_default=None)

    # Create verification_tokens table
    op.create_table(
        "verification_tokens",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("token", sa.String(255), nullable=False),
        sa.Column("is_used", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_verification_tokens_user_id"), "verification_tokens", ["user_id"])
    op.create_index(op.f("ix_verification_tokens_token"), "verification_tokens", ["token"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_verification_tokens_token"), table_name="verification_tokens")
    op.drop_index(op.f("ix_verification_tokens_user_id"), table_name="verification_tokens")
    op.drop_table("verification_tokens")
    op.drop_column("users", "is_verified")