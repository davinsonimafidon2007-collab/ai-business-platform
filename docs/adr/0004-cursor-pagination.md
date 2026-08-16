# ADR-004: Paginación por cursor (keyset) para listados grandes

- Estado: Aceptado
- Fecha: 2026-08-15
- Área: Rendimiento / API

## Contexto

Los listados (vehículos, oportunidades) usan paginación offset (`skip`/`limit`).
Con volúmenes grandes, OFFSET profundo degrada (PERF-001 / `MAX_LIST_DEPTH`).

## Decisión

Nuevo esquema `CursorPage[T]` y helper `CursorPaginator` en repos. La página
devuelve `next_cursor` (base64 de `created_at` + `id`) y la query usa
comparación keyset `(created_at, id) < (?, ?)` con ordenación
`created_at DESC, id DESC` (tie-break estable por id). Endpoints:
`GET /vehicles/cursor` y `GET /opportunities/cursor`.

## Justificación

- Consultas O(1) por página: sin escanear filas descartadas.
- Orden estable aunque `created_at` se repita (tie-break por id).
- El token es opaco (base64), válido para Postgres y SQLite 3.15+.
- El paginator permite eager-load (`selectinload`) para evitar lazy-load async.

## Consecuencias

- Respuesta ligeramente más compleja (token en vez de número de página).
- El COUNT total se mantiene, aunque es opcional para cursores puros.

## Alternativas

- Keyset por `id` solo: pierde estabilidad si hay creación másiva en el mismo
  segundo.
- Deep offset: simple pero lento a gran escala.