"""add vehicles, searches, and vehicle_evaluations tables

Revision ID: c1d2e3f4a5b6
Revises: b9c3d4e5f6a7
Create Date: 2026-07-25 23:20:00.000000

"""

from alembic import op
import sqlalchemy as sa


revision = "c1d2e3f4a5b6"
down_revision = "b9c3d4e5f6a7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create vehicles table
    op.create_table(
        "vehicles",
        sa.Column("id", sa.Uuid(as_uuid=False), nullable=False),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("external_id", sa.String(255), nullable=False),
        sa.Column("url", sa.Text, nullable=True),
        sa.Column("brand", sa.String(100), nullable=False),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column("version", sa.String(255), nullable=True),
        sa.Column("year", sa.Integer, nullable=True),
        sa.Column("mileage", sa.Integer, nullable=True),
        sa.Column("fuel_type", sa.String(50), nullable=True),
        sa.Column("transmission", sa.String(50), nullable=True),
        sa.Column("power_hp", sa.Integer, nullable=True),
        sa.Column("displacement_cc", sa.Integer, nullable=True),
        sa.Column("doors", sa.Integer, nullable=True),
        sa.Column("color", sa.String(50), nullable=True),
        sa.Column("emissions", sa.String(50), nullable=True),
        sa.Column("location", sa.String(255), nullable=True),
        sa.Column("seller_type", sa.String(50), nullable=True),
        sa.Column("first_registration", sa.String(50), nullable=True),
        sa.Column("price", sa.Float, nullable=True),
        sa.Column("currency", sa.String(10), nullable=True),
        sa.Column("vin", sa.String(50), nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("images", sa.Text, nullable=True),
        sa.Column("equipment", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_vehicles_source_external_id"), "vehicles", ["source", "external_id"], unique=True)

    # Create searches table
    op.create_table(
        "searches",
        sa.Column("id", sa.Uuid(as_uuid=False), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("country", sa.String(10), nullable=False),
        sa.Column("brands", sa.Text, nullable=True),
        sa.Column("models", sa.Text, nullable=True),
        sa.Column("filters", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create vehicle_evaluations table
    op.create_table(
        "vehicle_evaluations",
        sa.Column("id", sa.Uuid(as_uuid=False), nullable=False),
        sa.Column("vehicle_id", sa.Uuid(as_uuid=False), nullable=False),
        sa.Column("estimated_market_price_es", sa.Float, nullable=True),
        sa.Column("estimated_import_cost", sa.Float, nullable=True),
        sa.Column("estimated_registration_cost", sa.Float, nullable=True),
        sa.Column("estimated_total_cost", sa.Float, nullable=True),
        sa.Column("estimated_profit", sa.Float, nullable=True),
        sa.Column("profit_margin_percent", sa.Float, nullable=True),
        sa.Column("score", sa.Integer, nullable=True),
        sa.Column("classification", sa.String(10), nullable=True),
        sa.Column("warnings", sa.Text, nullable=True),
        sa.Column("recommendation", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["vehicle_id"], ["vehicles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_vehicle_evaluations_vehicle_id"), "vehicle_evaluations", ["vehicle_id"], unique=True
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_vehicle_evaluations_vehicle_id"), table_name="vehicle_evaluations")
    op.drop_table("vehicle_evaluations")
    op.drop_table("searches")
    op.drop_index(op.f("ix_vehicles_source_external_id"), table_name="vehicles")
    op.drop_table("vehicles")