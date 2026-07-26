"""add search_history, opportunities, cached_market_data tables

Revision ID: d5e6f7a8b9c0
Revises: c1d2e3f4a5b6
Create Date: 2026-07-26 10:00:00.000000

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "d5e6f7a8b9c0"
down_revision = "c1d2e3f4a5b6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create search_history table
    op.create_table(
        "search_history",
        sa.Column("id", sa.Uuid(as_uuid=False), nullable=False),
        sa.Column("query", sa.Text, nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("providers_used", sa.Text, nullable=True),
        sa.Column("results_count", sa.Integer, nullable=True),
        sa.Column("execution_time", sa.Float, nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_search_history_timestamp"),
        "search_history",
        ["timestamp"],
    )
    op.create_index(
        op.f("ix_search_history_query"),
        "search_history",
        ["query"],
        postgresql_ops={"query": "gin_trgm_ops"},
        postgresql_using="gin",
    )

    # Create opportunities table
    op.create_table(
        "opportunities",
        sa.Column("id", sa.Uuid(as_uuid=False), nullable=False),
        sa.Column("vehicle_id", sa.Uuid(as_uuid=False), nullable=False),
        sa.Column("opportunity_score", sa.Float, nullable=True),
        sa.Column("recommendation", sa.String(50), nullable=True),
        sa.Column("roi", sa.Float, nullable=True),
        sa.Column("risk", sa.String(20), nullable=True),
        sa.Column("profit", sa.Float, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("analyzed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("engine_version", sa.String(20), nullable=True),
        sa.ForeignKeyConstraint(
            ["vehicle_id"], ["vehicles.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_opportunities_vehicle_id"),
        "opportunities",
        ["vehicle_id"],
    )
    op.create_index(
        op.f("ix_opportunities_opportunity_score"),
        "opportunities",
        ["opportunity_score"],
    )

    # Create cached_market_data table
    op.create_table(
        "cached_market_data",
        sa.Column("id", sa.Uuid(as_uuid=False), nullable=False),
        sa.Column("external_id", sa.String(255), nullable=False),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("market_hash", sa.String(64), nullable=True),
        sa.Column("market_price", sa.Float, nullable=True),
        sa.Column("confidence", sa.Float, nullable=True),
        sa.Column("supply_level", sa.Float, nullable=True),
        sa.Column("demand_level", sa.Float, nullable=True),
        sa.Column("market_trend", sa.String(20), nullable=True),
        sa.Column("comparable_count", sa.Integer, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_cached_market_data_external_provider"),
        "cached_market_data",
        ["external_id", "provider"],
    )
    op.create_index(
        op.f("ix_cached_market_data_expires_at"),
        "cached_market_data",
        ["expires_at"],
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_cached_market_data_expires_at"),
        table_name="cached_market_data",
    )
    op.drop_index(
        op.f("ix_cached_market_data_external_provider"),
        table_name="cached_market_data",
    )
    op.drop_table("cached_market_data")

    op.drop_index(
        op.f("ix_opportunities_opportunity_score"),
        table_name="opportunities",
    )
    op.drop_index(
        op.f("ix_opportunities_vehicle_id"),
        table_name="opportunities",
    )
    op.drop_table("opportunities")

    op.drop_index(
        op.f("ix_search_history_query"),
        table_name="search_history",
    )
    op.drop_index(
        op.f("ix_search_history_timestamp"),
        table_name="search_history",
    )
    op.drop_table("search_history")

