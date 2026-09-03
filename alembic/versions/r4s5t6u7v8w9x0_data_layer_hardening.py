"""data layer hardening: FKs, indexes, constraints, server_defaults

Revision ID: r4s5t6u7v8w9x0
Revises: q3r4s5t6u7v8
Create Date: 2026-08-25

Fixes:
- verification_tokens & password_reset_tokens: add FK to users.id (CASCADE), type Uuid where postgres
- opportunity_phases: align id/opportunity_id to Uuid (was String(36) vs uuid FK), add unique(opportunity_id,order)
- vehicles: add ix_vehicles_vin, ix_vehicles_user_id, ix_vehicles_created_at
- opportunities: add ix_opportunities_vehicle_id, created_at
- cached_market_data: add unique(external_id,provider,market_hash), indexes for market_hash/expires_at
- search_order_vehicles: add unique(search_order_id,vehicle_id)
- inspection_sessions/observations/photos: add missing indexes and unique(session,category,item)
- audit_logs: add ix_audit_logs_resource_id
- server_default alignment for Boolean/timestamps handled at ORM level; BD defaults added where safe
"""

from alembic import op
import sqlalchemy as sa

revision = "r4s5t6u7v8w9x0"
down_revision = "q3r4s5t6u7v8"
branch_labels = None
depends_on = None


def _is_postgres() -> bool:
    bind = op.get_bind()
    return bind.dialect.name == "postgresql"


def upgrade() -> None:
    # -- verification_tokens & password_reset_tokens: add FK (and fix type for postgres) --
    # For postgres we need to cast String(36) -> uuid then add FK.
    # For sqlite, String is fine - just add FK via batch.
    if _is_postgres():
        # verification_tokens
        op.execute("DELETE FROM verification_tokens WHERE user_id IS NULL OR user_id !~* '^[0-9a-f-]{36}$'")
        op.execute("ALTER TABLE verification_tokens ALTER COLUMN user_id TYPE uuid USING user_id::uuid")
        # password_reset_tokens
        op.execute("DELETE FROM password_reset_tokens WHERE user_id IS NULL OR user_id !~* '^[0-9a-f-]{36}$'")
        op.execute("ALTER TABLE password_reset_tokens ALTER COLUMN user_id TYPE uuid USING user_id::uuid")
        # create FKs
        op.create_foreign_key(
            "fk_verification_tokens_user_id", "verification_tokens", "users", ["user_id"], ["id"], ondelete="CASCADE"
        )
        op.create_foreign_key(
            "fk_password_reset_tokens_user_id", "password_reset_tokens", "users", ["user_id"], ["id"], ondelete="CASCADE"
        )
        # opportunity_phases: fix id and opportunity_id to uuid
        op.execute("ALTER TABLE opportunity_phases ALTER COLUMN id TYPE uuid USING id::uuid")
        op.execute("ALTER TABLE opportunity_phases ALTER COLUMN opportunity_id TYPE uuid USING opportunity_id::uuid")
        # NOTA: ix_opportunity_phases_opportunity_order (unique opportunity_id+order)
        # ya lo crea q3r4s5t6u7v8_add_opportunity_phases_table.py al crear la tabla.
        # Recrearlo aquí rompía "alembic upgrade head" contra Postgres real con
        # asyncpg.exceptions.DuplicateTableError — en SQLite pasaba desapercibido
        # porque la rama de abajo lo envolvía en try/except.
    else:
        # sqlite: use batch to add FKs (sqlite FKs are not type-strict, String ok)
        # Alembic sqlite batch for FK creation
        with op.batch_alter_table("verification_tokens") as batch:
            try:
                batch.create_foreign_key("fk_verification_tokens_user_id", "users", ["user_id"], ["id"], ondelete="CASCADE")
            except Exception:
                pass
        with op.batch_alter_table("password_reset_tokens") as batch:
            try:
                batch.create_foreign_key("fk_password_reset_tokens_user_id", "users", ["user_id"], ["id"], ondelete="CASCADE")
            except Exception:
                pass
        # ix_opportunity_phases_opportunity_order: ya la crea
        # q3r4s5t6u7v8_add_opportunity_phases_table.py — ver nota en la rama postgres.

    # -- indexes --
    #
    # NOTA (bug real encontrado vía CI contra Postgres real, no detectable
    # con los tests unitarios en SQLite): el try/except de abajo NO hace
    # "crear solo si no existe" en Postgres. Una vez que UNA sentencia falla
    # dentro de una transacción, Postgres marca TODA la transacción como
    # abortada — el except de Python atrapa la excepción, pero no hace
    # ROLLBACK del error a nivel SQL, así que la siguiente sentencia (aunque
    # fuera válida) falla con "current transaction is aborted". En SQLite
    # esto no pasa (cada sentencia fallida no envenena las siguientes), por
    # eso los tests en SQLite nunca lo detectaron.
    #
    # Fix real: en Postgres, usar CREATE INDEX IF NOT EXISTS por SQL directo
    # (no falla nunca, no hay nada que atrapar). En SQLite se mantiene el
    # try/except (ahí sí es seguro) porque `IF NOT EXISTS` en índices únicos
    # con Alembic batch no es trivial de portar.
    #
    # Además, un barrido contra TODO el historial de migraciones encontró 5
    # duplicados reales más (creados ya antes en esta misma cadena): se
    # eliminan aquí en vez de intentar recrearlos.
    #   - ix_vehicles_user_id            -> d6e7f8a9b0c1
    #   - ix_opportunities_vehicle_id    -> d5e6f7a8b9c0
    #   - ix_vehicle_evaluations_vehicle_id -> c1d2e3f4a5b6
    #   - ix_search_order_vehicles_search_order_id -> h2i3j4k5l6m7
    #   - ix_search_order_vehicles_vehicle_id       -> h2i3j4k5l6m7
    if _is_postgres():

        def _create_index(name, table, cols, unique=False):
            kind = "UNIQUE INDEX" if unique else "INDEX"
            cols_sql = ", ".join(cols)
            op.execute(f'CREATE {kind} IF NOT EXISTS "{name}" ON {table} ({cols_sql})')
    else:

        def _create_index(name, table, cols, unique=False):
            try:
                op.create_index(name, table, cols, unique=unique)
            except Exception:
                pass

    _create_index("ix_vehicles_vin", "vehicles", ["vin"])
    _create_index("ix_vehicles_created_at", "vehicles", ["created_at"])
    _create_index("ix_opportunities_created_at", "opportunities", ["created_at"])
    _create_index("ix_cached_market_market_hash", "cached_market_data", ["market_hash"])
    _create_index("ix_cached_market_expires_at", "cached_market_data", ["expires_at"])
    _create_index("ix_inspection_sessions_vehicle_id", "inspection_sessions", ["vehicle_id"])
    _create_index("ix_inspection_sessions_user_id", "inspection_sessions", ["user_id"])
    _create_index("ix_inspection_sessions_created_at", "inspection_sessions", ["created_at"])
    _create_index("ix_inspection_observations_session_id", "inspection_observations", ["session_id"])
    _create_index("ix_inspection_observations_category_item", "inspection_observations", ["session_id", "category_id", "item_id"], unique=True)
    _create_index("ix_inspection_photos_observation_id", "inspection_photos", ["observation_id"])
    _create_index("ix_inspection_photos_session_id", "inspection_photos", ["session_id"])
    _create_index("ix_audit_logs_resource_id", "audit_logs", ["resource_id"])

    # unique constraints via indexes (portable)
    _create_index("uq_cached_market_external_provider_hash", "cached_market_data", ["external_id", "provider", "market_hash"], unique=True)
    _create_index("uq_search_order_vehicle", "search_order_vehicles", ["search_order_id", "vehicle_id"], unique=True)


def downgrade() -> None:
    def _drop(name, table):
        try:
            op.drop_index(name, table_name=table)
        except Exception:
            pass
        try:
            op.drop_constraint(name, table, type_="unique")
        except Exception:
            pass

    _drop("uq_search_order_vehicle", "search_order_vehicles")
    _drop("uq_cached_market_external_provider_hash", "cached_market_data")
    _drop("ix_audit_logs_resource_id", "audit_logs")
    _drop("ix_inspection_photos_session_id", "inspection_photos")
    _drop("ix_inspection_photos_observation_id", "inspection_photos")
    _drop("ix_inspection_observations_category_item", "inspection_observations")
    _drop("ix_inspection_observations_session_id", "inspection_observations")
    _drop("ix_inspection_sessions_created_at", "inspection_sessions")
    _drop("ix_inspection_sessions_user_id", "inspection_sessions")
    _drop("ix_inspection_sessions_vehicle_id", "inspection_sessions")
    _drop("ix_cached_market_expires_at", "cached_market_data")
    _drop("ix_cached_market_market_hash", "cached_market_data")
    _drop("ix_opportunities_created_at", "opportunities")
    _drop("ix_vehicles_created_at", "vehicles")
    _drop("ix_vehicles_vin", "vehicles")
    # ix_opportunity_phases_opportunity_order: la crea y la borra
    # q3r4s5t6u7v8_add_opportunity_phases_table.py, no esta migración.
    # ix_vehicles_user_id, ix_opportunities_vehicle_id,
    # ix_vehicle_evaluations_vehicle_id, ix_search_order_vehicles_search_order_id,
    # ix_search_order_vehicles_vehicle_id: no las crea esta migración (ver
    # comentario en upgrade()), no las borra tampoco.

    if _is_postgres():
        try:
            op.drop_constraint("fk_password_reset_tokens_user_id", "password_reset_tokens", type_="foreignkey")
        except Exception:
            pass
        try:
            op.drop_constraint("fk_verification_tokens_user_id", "verification_tokens", type_="foreignkey")
        except Exception:
            pass
        op.execute("ALTER TABLE verification_tokens ALTER COLUMN user_id TYPE varchar(36) USING user_id::text")
        op.execute("ALTER TABLE password_reset_tokens ALTER COLUMN user_id TYPE varchar(36) USING user_id::text")
        op.execute("ALTER TABLE opportunity_phases ALTER COLUMN id TYPE varchar(36) USING id::text")
        op.execute("ALTER TABLE opportunity_phases ALTER COLUMN opportunity_id TYPE varchar(36) USING opportunity_id::text")
    else:
        with op.batch_alter_table("verification_tokens") as batch:
            try:
                batch.drop_constraint("fk_verification_tokens_user_id", type_="foreignkey")
            except Exception:
                pass
        with op.batch_alter_table("password_reset_tokens") as batch:
            try:
                batch.drop_constraint("fk_password_reset_tokens_user_id", type_="foreignkey")
            except Exception:
                pass
