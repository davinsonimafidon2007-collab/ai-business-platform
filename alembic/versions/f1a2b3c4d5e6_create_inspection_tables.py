"""create inspection tables

Revision ID: f1a2b3c4d5e6
Revises: e1f2a3b4c5d6
Create Date: 2026-07-31 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "f1a2b3c4d5e6"
down_revision = "e1f2a3b4c5d6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "inspection_sessions",
        sa.Column("id", sa.Uuid(as_uuid=False), primary_key=True),
        sa.Column(
            "vehicle_id",
            sa.Uuid(as_uuid=False),
            sa.ForeignKey("vehicles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.Uuid(as_uuid=False),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("current_category_order", sa.Integer, nullable=False),
        sa.Column("total_repair_cost", sa.Float, nullable=False),
        sa.Column("total_defects", sa.Integer, nullable=False),
        sa.Column("total_critical_defects", sa.Integer, nullable=False),
        sa.Column("risk_level", sa.String(20), nullable=True),
        sa.Column("recommendation", sa.Text, nullable=True),
        sa.Column("overall_condition", sa.Integer, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("summary_json", sa.Text, nullable=True),
    )

    op.create_table(
        "inspection_observations",
        sa.Column("id", sa.Uuid(as_uuid=False), primary_key=True),
        sa.Column(
            "session_id",
            sa.Uuid(as_uuid=False),
            sa.ForeignKey("inspection_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("category_id", sa.String(50), nullable=False),
        sa.Column("item_id", sa.String(50), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("estimated_repair_cost", sa.Float, nullable=True),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "inspection_photos",
        sa.Column("id", sa.Uuid(as_uuid=False), primary_key=True),
        sa.Column(
            "observation_id",
            sa.Uuid(as_uuid=False),
            sa.ForeignKey("inspection_observations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "session_id",
            sa.Uuid(as_uuid=False),
            sa.ForeignKey("inspection_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("file_path", sa.String(500), nullable=False),
        sa.Column("file_name", sa.String(255), nullable=True),
        sa.Column("mime_type", sa.String(100), nullable=True),
        sa.Column("file_size_bytes", sa.Integer, nullable=True),
        sa.Column("ai_analysis_status", sa.String(20), nullable=False),
        sa.Column("ai_analysis_result", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("inspection_photos")
    op.drop_table("inspection_observations")
    op.drop_table("inspection_sessions")