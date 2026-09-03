"""TASK 9 (AUD-017/018) — índices e integridad referencial reales.

SQLite (usado en el resto de la suite) no fuerza foreign keys por defecto,
así que un INSERT huérfano no lanzaría aquí aunque la constraint no
existiera — probarlo contra SQLite daría una falsa sensación de seguridad.
En su lugar, estos tests fijan las garantías al nivel de metadata de
SQLAlchemy (tipo de columna, tabla/columna referenciada, ondelete), que es
justo lo que la migración `t6u7v8w9x0y1` traduce a DDL real de Postgres.
"""

from __future__ import annotations

from sqlalchemy import Uuid

from app.models.audit_log import AuditLog
from app.models.inspection import (
    InspectionObservation,
    InspectionPhoto,
    InspectionSession,
)
from app.models.password_reset_token import PasswordResetToken
from app.models.user import User
from app.models.verification_token import VerificationToken


def _fk_target(column) -> tuple[str, str] | None:
    """(tabla, columna) referenciadas por la primera FK de una columna, o None."""
    for fk in column.foreign_keys:
        return fk.column.table.name, fk.column.name
    return None


class TestTokenForeignKeys:
    """AUD-018: user_id en tokens era varchar(36) sin FK real."""

    def test_password_reset_token_user_id_references_users(self) -> None:
        column = PasswordResetToken.__table__.c.user_id
        assert _fk_target(column) == ("users", "id")
        assert isinstance(column.type, Uuid)
        assert column.index is True

    def test_password_reset_token_fk_cascades_on_user_delete(self) -> None:
        fk = next(iter(PasswordResetToken.__table__.c.user_id.foreign_keys))
        assert fk.ondelete == "CASCADE"

    def test_verification_token_user_id_references_users(self) -> None:
        column = VerificationToken.__table__.c.user_id
        assert _fk_target(column) == ("users", "id")
        assert isinstance(column.type, Uuid)

    def test_verification_token_fk_cascades_on_user_delete(self) -> None:
        fk = next(iter(VerificationToken.__table__.c.user_id.foreign_keys))
        assert fk.ondelete == "CASCADE"

    def test_user_id_column_type_matches_users_pk_type(self) -> None:
        """El tipo de la FK debe coincidir con el de users.id (antes no coincidía)."""
        users_pk_type = type(User.__table__.c.id.type)
        assert type(PasswordResetToken.__table__.c.user_id.type) is users_pk_type
        assert type(VerificationToken.__table__.c.user_id.type) is users_pk_type
        assert type(AuditLog.__table__.c.user_id.type) is users_pk_type


class TestAuditLogForeignKey:
    """AuditLog es un log inmutable: no debe perderse al borrar el usuario."""

    def test_user_id_references_users(self) -> None:
        column = AuditLog.__table__.c.user_id
        assert _fk_target(column) == ("users", "id")
        assert column.nullable is True

    def test_fk_sets_null_on_user_delete_not_cascade(self) -> None:
        """SET NULL, no CASCADE: borrar un usuario no debe borrar su historial."""
        fk = next(iter(AuditLog.__table__.c.user_id.foreign_keys))
        assert fk.ondelete == "SET NULL"

    def test_resource_id_stays_unconstrained_by_design(self) -> None:
        """resource_id es polimórfico (según `resource`): no apunta a una
        única tabla, así que NO debe llevar FK."""
        column = AuditLog.__table__.c.resource_id
        assert len(column.foreign_keys) == 0


def _has_index_on(table, *columns: str) -> bool:
    """True si alguna Index() de la tabla cubre exactamente estas columnas
    (como primeras columnas, en cualquier índice compuesto o simple)."""
    wanted = list(columns)
    for index in table.indexes:
        cols = [c.name for c in index.columns]
        if cols[: len(wanted)] == wanted:
            return True
    return False


class TestInspectionIndexes:
    """AUD-017: ninguna FK de las tablas de inspección tenía índice.

    Los índices se declaran en ``__table_args__`` (fusionado con
    origin/main), no como ``index=True`` por columna: declararlo de las dos
    formas a la vez crea el mismo índice dos veces con el mismo nombre
    auto-generado, lo que rompe ``create_all`` en SQLite.
    """

    def test_session_vehicle_id_indexed(self) -> None:
        assert _has_index_on(InspectionSession.__table__, "vehicle_id")

    def test_session_user_id_indexed(self) -> None:
        assert _has_index_on(InspectionSession.__table__, "user_id")

    def test_observation_session_id_indexed(self) -> None:
        assert _has_index_on(InspectionObservation.__table__, "session_id")

    def test_photo_observation_id_indexed(self) -> None:
        assert _has_index_on(InspectionPhoto.__table__, "observation_id")

    def test_photo_session_id_indexed(self) -> None:
        assert _has_index_on(InspectionPhoto.__table__, "session_id")
