"""add push_tokens table

Revision ID: m3n4o5p6q7r8
Revises: l2m3n4o5p6q7
Create Date: 2026-08-14

MOB-P1-001: tabla de tokens FCM de push notifications por usuario.
Cada usuario tiene un único token por plataforma (upsert en el endpoint
POST /notifications/register).
"""

from alembic import op
import sqlalchemy as sa


revision = "m3n4o5p6q7r8"
down_revision = "l2m3n4o5p6q7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "push_tokens",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("token", sa.String(255), nullable=False),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("platform", sa.String(50), nullable=False, server_default="android"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_push_tokens_token"), "push_tokens", ["token"], unique=True)
    op.create_index(op.f("ix_push_tokens_user_id"), "push_tokens", ["user_id"])
    op.create_unique_constraint(
        "uq_push_tokens_user_platform",
        "push_tokens",
        ["user_id", "platform"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_push_tokens_user_platform", "push_tokens", type_="unique")
    op.drop_index(op.f("ix_push_tokens_user_id"), table_name="push_tokens")
    op.drop_index(op.f("ix_push_tokens_token"), table_name="push_tokens")
    op.drop_table("push_tokens")
