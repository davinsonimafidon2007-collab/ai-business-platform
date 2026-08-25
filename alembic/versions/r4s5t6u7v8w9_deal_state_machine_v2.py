"""deal state machine v2: rename statuses + audit history + concurrency

Revision ID: r4s5t6u7v8w9
Revises: q3r4s5t6u7v8
Create Date: 2026-08-25 00:00:00.000000

Cambios:
- deal_status: CONTACTED -> ANALYZING, OFFER -> NEGOTIATING, DROPPED -> CANCELLED
- deals.status_changed_at / closed_at / version (bloqueo optimista)
- tabla deal_status_history (auditoría inmutable de transiciones)
- índice único parcial uq_deals_active_per_opportunity (un deal activo por
  oportunidad y usuario, garantizado en BD)
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "r4s5t6u7v8w9"
down_revision = "q3r4s5t6u7v8"
branch_labels = None
depends_on = None

OLD_ACTIVE_VALUES = ("NEW", "CONTACTED", "OFFER")
NEW_ACTIVE_VALUES = ("NEW", "ANALYZING", "NEGOTIATING")

RENAME_MAP = (
    ("CONTACTED", "ANALYZING"),
    ("OFFER", "NEGOTIATING"),
    ("DROPPED", "CANCELLED"),
)

TERMINAL_VALUES_SQL = "('WON', 'LOST', 'CANCELLED')"


def _upgrade_postgres_enum() -> None:
    # Renombrar labels del ENUM conserva los datos existentes.
    for old, new in RENAME_MAP:
        op.execute(
            f"ALTER TYPE deal_status RENAME VALUE '{old}' TO '{new}'"
        )


def _downgrade_postgres_enum() -> None:
    for old, new in RENAME_MAP:
        op.execute(
            f"ALTER TYPE deal_status RENAME VALUE '{new}' TO '{old}'"
        )


def _upgrade_sqlite_enum() -> None:
    """SQLite: el enum es VARCHAR + CHECK; recrear la columna en dos pasadas."""
    old_enum = sa.Enum(
        "NEW",
        "CONTACTED",
        "OFFER",
        "WON",
        "LOST",
        "DROPPED",
        name="deal_status",
    )
    with op.batch_alter_table("deals") as batch_op:
        batch_op.alter_column(
            "status",
            existing_type=old_enum,
            type_=sa.String(length=20),
            existing_nullable=False,
        )
    for old, new in RENAME_MAP:
        op.execute(f"UPDATE deals SET status = '{new}' WHERE status = '{old}'")
    new_enum = sa.Enum(
        "NEW",
        "ANALYZING",
        "NEGOTIATING",
        "WON",
        "LOST",
        "CANCELLED",
        name="deal_status",
    )
    with op.batch_alter_table("deals") as batch_op:
        batch_op.alter_column(
            "status",
            existing_type=sa.String(length=20),
            type_=new_enum,
            existing_nullable=False,
        )


def _downgrade_sqlite_enum() -> None:
    new_enum = sa.Enum(
        "NEW",
        "ANALYZING",
        "NEGOTIATING",
        "WON",
        "LOST",
        "CANCELLED",
        name="deal_status",
    )
    with op.batch_alter_table("deals") as batch_op:
        batch_op.alter_column(
            "status",
            existing_type=new_enum,
            type_=sa.String(length=20),
            existing_nullable=False,
        )
    for old, new in RENAME_MAP:
        op.execute(f"UPDATE deals SET status = '{old}' WHERE status = '{new}'")
    old_enum = sa.Enum(
        "NEW",
        "CONTACTED",
        "OFFER",
        "WON",
        "LOST",
        "DROPPED",
        name="deal_status",
    )
    with op.batch_alter_table("deals") as batch_op:
        batch_op.alter_column(
            "status",
            existing_type=sa.String(length=20),
            type_=old_enum,
            existing_nullable=False,
        )


def upgrade() -> None:
    bind = op.get_bind()

    # 1) Renombrar valores del enum (Postgres) o recrear CHECK (SQLite).
    if bind.dialect.name == "postgresql":
        _upgrade_postgres_enum()
    else:
        _upgrade_sqlite_enum()

    # 2) Nuevas columnas de estado/tiempo/concurrencia.
    op.add_column(
        "deals",
        sa.Column(
            "status_changed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.add_column(
        "deals",
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "deals",
        sa.Column("version", sa.Integer(), server_default="0", nullable=False),
    )

    # 3) Backfill: deals ya cerrados reciben closed_at.
    op.execute(f"UPDATE deals SET closed_at = updated_at WHERE status IN {TERMINAL_VALUES_SQL}")

    # 4) Tabla de auditoría de transiciones (inmutable).
    op.create_table(
        "deal_status_history",
        sa.Column("id", sa.Uuid(as_uuid=False), nullable=False),
        sa.Column(
            "deal_id",
            sa.Uuid(as_uuid=False),
            nullable=False,
        ),
        sa.Column("from_status", sa.String(length=20), nullable=True),
        sa.Column("to_status", sa.String(length=20), nullable=False),
        sa.Column("changed_by_user_id", sa.Uuid(as_uuid=False), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("offer_price", sa.Numeric(12, 2), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["deal_id"],
            ["deals.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_deal_status_history_deal_id",
        "deal_status_history",
        ["deal_id"],
    )

    # 5) Deduplicar deals activos por (user_id, opportunity_id): se conserva
    #    el más reciente. Necesario antes del índice único parcial.
    active_values_sql = ", ".join(repr(v) for v in NEW_ACTIVE_VALUES)
    op.execute(
        f"""
        DELETE FROM deals
        WHERE status IN ({active_values_sql})
          AND opportunity_id IS NOT NULL
          AND id NOT IN (
              SELECT id FROM (
                  SELECT id,
                         ROW_NUMBER() OVER (
                             PARTITION BY user_id, opportunity_id
                             ORDER BY created_at DESC, id DESC
                         ) AS rn
                  FROM deals
                  WHERE status IN ({active_values_sql})
                    AND opportunity_id IS NOT NULL
              ) ranked
              WHERE ranked.rn = 1
          )
        """
    )

    # 6) Garantía real de unicidad a nivel BD (índice único parcial).
    partial_where = sa.text(f"status IN ({active_values_sql})")
    op.create_index(
        "uq_deals_active_per_opportunity",
        "deals",
        ["user_id", "opportunity_id"],
        unique=True,
        postgresql_where=partial_where,
        sqlite_where=partial_where,
    )


def downgrade() -> None:
    bind = op.get_bind()

    op.drop_index("uq_deals_active_per_opportunity", table_name="deals")
    op.drop_index("ix_deal_status_history_deal_id", table_name="deal_status_history")
    op.drop_table("deal_status_history")
    op.drop_column("deals", "version")
    op.drop_column("deals", "closed_at")
    op.drop_column("deals", "status_changed_at")

    if bind.dialect.name == "postgresql":
        _downgrade_postgres_enum()
    else:
        _downgrade_sqlite_enum()
