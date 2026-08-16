"""Cursor (keyset) pagination helper for repositories (TASK-019).

Fallback de paginación para listados grandes sin OFFSET profundo: se consulta
``limit+1`` filas ordenadas por ``created_at DESC, id DESC`` y, si sobra una,
hay más páginas. El token de cursor se genera con el último item devuelto.
La cola de ordenación se hace con comparación de tuplas
``(created_at, id) < (?, ?)``, válida en Postgres y SQLite 3.15+.
"""

from __future__ import annotations

from sqlalchemy import func, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import Base
from app.schemas.pagination import decode_cursor, encode_cursor


class CursorPaginator:
    """Paginador keyset generico para un modelo SQLAlchemy.

    Se reutiliza en ``VehicleRepository.list_cursor`` y
    ``OpportunityRepository.list_cursor`` (misma orden: created_at DESC, id DESC).

    Args:
        session: sesión async activa.
        model: clase del modelo (p.ej. ``Vehicle``).
    """

    def __init__(self, session: AsyncSession, model: type[Base]) -> None:
        self.session = session
        self.model = model

    async def paginate(
        self,
        cursor: str | None,
        limit: int,
        where: list | None = None,
        count_where: list | None = None,
        options: list | None = None,
    ) -> tuple[list, int, bool, str | None]:
        """Devuelve ``(items, total, has_more, next_cursor)``.

        Args:
            cursor: token base64 de la página anterior (``None`` = primera).
            limit: tamaño de página.
            where: lista de condiciones SQLAlchemy para **items** (opcional).
            count_where: condiciones equivalentes para el COUNT total
                (por defecto se reutiliza ``where``).
            options: opciones SQLAlchemy tipo ``selectinload`` a aplicar a la
                query de items (evita lazy-load en sesión async).
        """
        created_at_vals = (self.model.created_at, self.model.id)
        keep = max(1, limit)
        query = select(self.model)

        cursor_created_at, cursor_id = decode_cursor(cursor)
        if cursor_created_at is not None and cursor_id is not None:
            # Keyset: todo lo que viene "antes" que el punto del cursor (igual
            # ordenación DESC, tie-break por id para created_at repetidos).
            query = query.where(
                tuple_(*created_at_vals).__lt__(
                    tuple_(cursor_created_at, cursor_id)
                )
            )

        if where:
            query = query.where(*where)
        if options:
            query = query.options(*options)

        query = (
            query.order_by(self.model.created_at.desc(), self.model.id.desc())
            .limit(keep + 1)
        )
        result = await self.session.execute(query)
        rows = list(result.scalars().all())

        has_more = len(rows) > keep
        items = rows[:keep]

        next_cursor: str | None = None
        if has_more:
            last = items[-1]
            next_cursor = encode_cursor(last.created_at, str(last.id))

        # COUNT total con el mismo filtro (el keyset NO aplica al total).
        count_query = select(func.count(self.model.id)).select_from(self.model)
        if count_where is not None:
            count_query = count_query.where(*count_where)
        elif where:
            count_query = count_query.where(*where)
        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        return items, total, has_more, next_cursor