"""Migrate images from comma-separated string to JSON array.

Revision ID: k3l4m5n6o7p8
Revises: j2k3l4m5n6o7
Create Date: 2026-08-10
"""

import json

from alembic import op
import sqlalchemy as sa

revision = "k3l4m5n6o7p8"
down_revision = "j2k3l4m5n6o7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add a temporary JSON column
    op.add_column(
        "vehicles",
        sa.Column("images_json", sa.JSON, nullable=True),
    )

    # Copy data from comma-separated string to JSON array
    conn = op.get_bind()
    result = conn.execute(sa.text("SELECT id, images FROM vehicles WHERE images IS NOT NULL"))
    for row in result:
        images_str = row[1]
        if images_str:
            images_list = [img.strip() for img in images_str.split(",") if img.strip()]
            conn.execute(
                sa.text("UPDATE vehicles SET images_json = :images WHERE id = :id"),
                {"images": json.dumps(images_list), "id": row[0]},
            )

    # Drop old column and rename new one
    op.drop_column("vehicles", "images")
    op.alter_column(
        "vehicles",
        "images_json",
        new_column_name="images",
        type_=sa.JSON,
        postgresql_using="images_json::json",
    )


def downgrade() -> None:
    # Reverse: JSON array back to comma-separated string
    op.add_column(
        "vehicles",
        sa.Column("images_csv", sa.Text, nullable=True),
    )

    conn = op.get_bind()
    result = conn.execute(sa.text("SELECT id, images FROM vehicles WHERE images IS NOT NULL"))
    for row in result:
        images_json = row[1]
        if images_json:
            images_list = json.loads(images_json) if isinstance(images_json, str) else images_json
            csv_str = ",".join(images_list) if images_list else None
            conn.execute(
                sa.text("UPDATE vehicles SET images_csv = :images WHERE id = :id"),
                {"images": csv_str, "id": row[0]},
            )

    op.drop_column("vehicles", "images")
    op.alter_column(
        "vehicles",
        "images_csv",
        new_column_name="images",
        type_=sa.Text,
        postgresql_using="images_csv",
    )
