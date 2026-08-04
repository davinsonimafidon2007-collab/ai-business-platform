"""add deals table

Revision ID: e2f3a4b5c6d7
Revises: f8a9b0c1d2e3
Create Date: 2026-08-03 00:00:00.000000

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "e2f3a4b5c6d7"
down_revision = "f8a9b0c1d2e3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "deals",
        sa.Column("id", sa.Uuid(as_uuid=False), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=False), nullable=False),
        sa.Column("vehicle_id", sa.Uuid(as_uuid=False), nullable=True),
        sa.Column("opportunity_id", sa.Uuid(as_uuid=False), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "NEW",
                "CONTACTED",
                "OFFER",
                "WON",
                "LOST",
                "DROPPED",
                name="deal_status",
            ),
            nullable=False,
        ),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("offer_price", sa.Numeric(12, 2), nullable=True),
        sa.Column("contact_channel", sa.String(20), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["vehicle_id"], ["vehicles.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["opportunity_id"], ["opportunities.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_deals_user_id"),
        "deals",
        ["user_id"],
    )
    op.create_index(
        op.f("ix_deals_status"),
        "deals",
        ["status"],
    )
    op.create_index(
        op.f("ix_deals_vehicle_id"),
        "deals",
        ["vehicle_id"],
    )
    op.create_index(
        op.f("ix_deals_opportunity_id"),
        "deals",
        ["opportunity_id"],
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_deals_opportunity_id"), table_name="deals")
    op.drop_index(op.f("ix_deals_vehicle_id"), table_name="deals")
    op.drop_index(op.f("ix_deals_status"), table_name="deals")
    op.drop_index(op.f("ix_deals_user_id"), table_name="deals")
    op.drop_table("deals")
    # Drop the enum type created by the migration
    op.execute("DROP TYPE IF EXISTS deal_status")
