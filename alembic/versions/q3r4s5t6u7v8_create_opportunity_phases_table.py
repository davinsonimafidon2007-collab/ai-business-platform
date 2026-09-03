"""create opportunity_phases table

Revision ID: q3r4s5t6u7v8
Revises: p2q3r4s5t6u7
Create Date: 2026-09-03 00:00:00.000000

AUD-003 / AUD-004: el modelo OpportunityPhase (app/models/opportunity_phase.py)
existe y es usado por endpoints reales (GET/PATCH /opportunities/{id}/phases)
pero nunca tuvo migración: contra una base de datos limpia, alembic upgrade
head no fallaba pero la tabla opportunity_phases no existía, y esos endpoints
fallaban con "relation opportunity_phases does not exist". id/opportunity_id
se crean como uuid nativo (no varchar(36)) para coincidir con el tipo de
opportunities.id (sa.Uuid(as_uuid=False)).
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "q3r4s5t6u7v8"
down_revision = "p2q3r4s5t6u7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "opportunity_phases",
        sa.Column("id", sa.Uuid(as_uuid=False), nullable=False),
        sa.Column("opportunity_id", sa.Uuid(as_uuid=False), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "in_progress",
                "pending_approval",
                "completed",
                "aborted",
                name="opportunity_phase_status",
            ),
            nullable=False,
        ),
        sa.Column("agent", sa.String(100), nullable=True),
        sa.Column("order", sa.Integer, nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("feedback", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["opportunity_id"], ["opportunities.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_opportunity_phases_opportunity_id"),
        "opportunity_phases",
        ["opportunity_id"],
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_opportunity_phases_opportunity_id"),
        table_name="opportunity_phases",
    )
    op.drop_table("opportunity_phases")
    op.execute("DROP TYPE IF EXISTS opportunity_phase_status")
