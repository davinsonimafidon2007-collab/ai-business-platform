"""add opportunity_phases table for workflow

Revision ID: q3r4s5t6u7v8
Revises: p2q3r4s5t6u7
Create Date: 2026-08-24

Fix: app/models/opportunity_phase.py existía pero sin migración.
Sin esta tabla, GET /opportunities/{id}/phases falla con
relation "opportunity_phases" does not exist.
"""

from alembic import op
import sqlalchemy as sa


revision = "q3r4s5t6u7v8"
down_revision = "p2q3r4s5t6u7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "opportunity_phases",
        sa.Column("id", sa.String(length=36), nullable=False, primary_key=True),
        sa.Column("opportunity_id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
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
            server_default="pending",
        ),
        sa.Column("agent", sa.String(length=100), nullable=True),
        sa.Column("order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("feedback", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["opportunity_id"], ["opportunities.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_opportunity_phases_opportunity_id", "opportunity_phases", ["opportunity_id"])
    op.create_index("ix_opportunity_phases_status", "opportunity_phases", ["status"])


def downgrade() -> None:
    op.drop_index("ix_opportunity_phases_status", table_name="opportunity_phases")
    op.drop_index("ix_opportunity_phases_opportunity_id", table_name="opportunity_phases")
    op.drop_table("opportunity_phases")
    # El tipo Enum queda huérfano si no se borra
    sa.Enum(name="opportunity_phase_status").drop(op.get_bind(), checkfirst=True)
