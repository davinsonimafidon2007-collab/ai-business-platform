"""FK user_id on api_keys and refresh_tokens (align types to uuid)

Revision ID: f8a9b0c1d2e3
Revises: e7f8a9b0c1d2
Create Date: 2026-08-02 04:00:00.000000

users.id is uuid. api_keys.user_id and refresh_tokens.user_id were
varchar(36). Postgres cannot create a FK across those types.
This migration:
  1) deletes orphan rows
  2) casts user_id columns to uuid
  3) creates CASCADE FKs
"""

from __future__ import annotations

from alembic import op


revision = "f8a9b0c1d2e3"
down_revision = "e7f8a9b0c1d2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1) Orphans (compare as text while still varchar)
    op.execute(
        """
        DELETE FROM api_keys a
        WHERE a.user_id IS NOT NULL
          AND NOT EXISTS (
              SELECT 1 FROM users u WHERE u.id::text = a.user_id
          )
        """
    )
    op.execute(
        """
        DELETE FROM refresh_tokens r
        WHERE r.user_id IS NOT NULL
          AND NOT EXISTS (
              SELECT 1 FROM users u WHERE u.id::text = r.user_id
          )
        """
    )

    # 2) Align column types to uuid (same as users.id)
    op.execute(
        "ALTER TABLE api_keys "
        "ALTER COLUMN user_id TYPE uuid USING user_id::uuid"
    )
    op.execute(
        "ALTER TABLE refresh_tokens "
        "ALTER COLUMN user_id TYPE uuid USING user_id::uuid"
    )

    # 3) Foreign keys
    op.create_foreign_key(
        "fk_api_keys_user_id_users",
        "api_keys",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_refresh_tokens_user_id_users",
        "refresh_tokens",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_refresh_tokens_user_id_users",
        "refresh_tokens",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_api_keys_user_id_users",
        "api_keys",
        type_="foreignkey",
    )
    op.execute(
        "ALTER TABLE api_keys "
        "ALTER COLUMN user_id TYPE varchar(36) USING user_id::text"
    )
    op.execute(
        "ALTER TABLE refresh_tokens "
        "ALTER COLUMN user_id TYPE varchar(36) USING user_id::text"
    )
