"""TASK 3: deal fulfillment fields, deal_status enum extension, opportunity status

Revision ID: s5t6u7v8w9x0
Revises: u7v8w9x0y1z2
Create Date: 2026-09-03 00:00:00.000000

- Extiende el enum ``deal_status`` (Postgres) con BOUGHT, IN_TRANSIT,
  REGISTERED, SOLD (además de los ya existentes NEW/ANALYZING/NEGOTIATING/
  WON/LOST/CANCELLED — renombrados por deal_state_machine_v2, fusionado
  desde origin/main). ALTER TYPE ... ADD VALUE no puede ejecutarse dentro
  de un bloque transaccional en Postgres, así que se usa autocommit para
  esta parte de la migración.
- Añade a ``deals`` los campos de snapshot de negociación y de cumplimiento
  físico (compra real, transporte, matriculación, venta, beneficio real).
- Añade ``opportunities.status`` (OPEN/CONVERTED, default OPEN) para poder
  filtrar oportunidades ya convertidas a deal (AUD-010) y para que la
  conversión automática opportunity->deal no duplique deals.
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "s5t6u7v8w9x0"
down_revision = "u7v8w9x0y1z2"
branch_labels = None
depends_on = None

_NEW_DEAL_STATUS_VALUES = ("BOUGHT", "IN_TRANSIT", "REGISTERED", "SOLD")


def upgrade() -> None:
    # --- Extender el enum deal_status (fuera de transacción) ---
    with op.get_context().autocommit_block():
        for value in _NEW_DEAL_STATUS_VALUES:
            op.execute(f"ALTER TYPE deal_status ADD VALUE IF NOT EXISTS '{value}'")

    # --- Snapshot de negociación en deals ---
    op.add_column("deals", sa.Column("negotiation_initial_offer", sa.Numeric(12, 2), nullable=True))
    op.add_column("deals", sa.Column("negotiation_max_price", sa.Numeric(12, 2), nullable=True))
    op.add_column("deals", sa.Column("negotiation_walk_away_price", sa.Numeric(12, 2), nullable=True))
    op.add_column("deals", sa.Column("negotiation_recommendation", sa.String(20), nullable=True))
    op.add_column("deals", sa.Column("negotiation_snapshot_at", sa.DateTime(timezone=True), nullable=True))

    # --- Cumplimiento físico: compra ---
    op.add_column("deals", sa.Column("actual_purchase_price", sa.Numeric(12, 2), nullable=True))
    op.add_column("deals", sa.Column("bought_at", sa.DateTime(timezone=True), nullable=True))

    # --- Transporte ---
    op.add_column("deals", sa.Column("transport_carrier", sa.String(200), nullable=True))
    op.add_column("deals", sa.Column("transport_cost", sa.Numeric(12, 2), nullable=True))
    op.add_column("deals", sa.Column("transport_started_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("deals", sa.Column("transport_completed_at", sa.DateTime(timezone=True), nullable=True))

    # --- Matriculación ---
    op.add_column("deals", sa.Column("registration_plate", sa.String(20), nullable=True))
    op.add_column("deals", sa.Column("registration_cost", sa.Numeric(12, 2), nullable=True))
    op.add_column("deals", sa.Column("registered_at", sa.DateTime(timezone=True), nullable=True))

    # --- Venta ---
    op.add_column("deals", sa.Column("sale_price", sa.Numeric(12, 2), nullable=True))
    op.add_column("deals", sa.Column("buyer_name", sa.String(200), nullable=True))
    op.add_column("deals", sa.Column("buyer_contact", sa.String(200), nullable=True))
    op.add_column("deals", sa.Column("sold_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("deals", sa.Column("actual_profit", sa.Numeric(12, 2), nullable=True))

    # --- Opportunity.status ---
    op.add_column(
        "opportunities",
        sa.Column("status", sa.String(20), nullable=False, server_default="OPEN"),
    )
    op.alter_column("opportunities", "status", server_default=None)
    op.create_index(
        op.f("ix_opportunities_status"), "opportunities", ["status"]
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_opportunities_status"), table_name="opportunities")
    op.drop_column("opportunities", "status")

    op.drop_column("deals", "actual_profit")
    op.drop_column("deals", "sold_at")
    op.drop_column("deals", "buyer_contact")
    op.drop_column("deals", "buyer_name")
    op.drop_column("deals", "sale_price")

    op.drop_column("deals", "registered_at")
    op.drop_column("deals", "registration_cost")
    op.drop_column("deals", "registration_plate")

    op.drop_column("deals", "transport_completed_at")
    op.drop_column("deals", "transport_started_at")
    op.drop_column("deals", "transport_cost")
    op.drop_column("deals", "transport_carrier")

    op.drop_column("deals", "bought_at")
    op.drop_column("deals", "actual_purchase_price")

    op.drop_column("deals", "negotiation_snapshot_at")
    op.drop_column("deals", "negotiation_recommendation")
    op.drop_column("deals", "negotiation_walk_away_price")
    op.drop_column("deals", "negotiation_max_price")
    op.drop_column("deals", "negotiation_initial_offer")

    # Nota: Postgres no soporta ALTER TYPE ... DROP VALUE — no se puede
    # revertir la extensión del enum deal_status. Si alguna fila usa los
    # nuevos valores (BOUGHT/IN_TRANSIT/REGISTERED/SOLD), este downgrade
    # fallaría igualmente al intentar borrar filas con ese status; se deja
    # como limitación conocida y documentada (igual que otros enums nativos
    # del proyecto).
