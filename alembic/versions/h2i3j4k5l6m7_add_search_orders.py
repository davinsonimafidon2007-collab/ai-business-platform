"""add search_orders and search_order_vehicles

Revision ID: h2i3j4k5l6m7
Revises: g1h2i3j4k5l6
Create Date: 2026-08-09 00:00:00.000000

Órdenes de búsqueda en background (PERSONAL.NOAUTH): el usuario crea una
orden con query + presupuesto; un job del scheduler la procesa y persiste
los vehículos encontrados. ``search_order_vehicles`` vincula cada vehículo
a la orden con el estado "visto" para el badge de nuevos.
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "h2i3j4k5l6m7"
down_revision = "g1h2i3j4k5l6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "search_orders",
        sa.Column("id", sa.Uuid(as_uuid=False), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=False), nullable=False),
        sa.Column("query", sa.String(length=500), nullable=False),
        sa.Column("total_budget", sa.Float(), nullable=True),
        sa.Column("max_purchase_price", sa.Float(), nullable=True),
        sa.Column("filters", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("results_count", sa.Integer(), nullable=False),
        sa.Column("new_count", sa.Integer(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_search_orders_user_id"), "search_orders", ["user_id"], unique=False
    )

    op.create_table(
        "search_order_vehicles",
        sa.Column("id", sa.Uuid(as_uuid=False), nullable=False),
        sa.Column("search_order_id", sa.Uuid(as_uuid=False), nullable=False),
        sa.Column("vehicle_id", sa.Uuid(as_uuid=False), nullable=False),
        sa.Column("seen", sa.Boolean(), nullable=False),
        sa.Column("result_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["search_order_id"], ["search_orders.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["vehicle_id"], ["vehicles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_search_order_vehicles_search_order_id"),
        "search_order_vehicles",
        ["search_order_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_search_order_vehicles_vehicle_id"),
        "search_order_vehicles",
        ["vehicle_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_search_order_vehicles_vehicle_id"),
        table_name="search_order_vehicles",
    )
    op.drop_index(
        op.f("ix_search_order_vehicles_search_order_id"),
        table_name="search_order_vehicles",
    )
    op.drop_table("search_order_vehicles")
    op.drop_index(op.f("ix_search_orders_user_id"), table_name="search_orders")
    op.drop_table("search_orders")
