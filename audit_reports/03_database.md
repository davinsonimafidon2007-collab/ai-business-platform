# Auditoría — Base de datos y migraciones
Fecha: 2026-08-20
Commit auditado: cc2a256a433d998531be578517b3abdaf1217996

## Hallazgos confirmados (con evidencia)
- `alembic/` no existe en el árbol revisado; no hay paquete de migraciones rastreable desde el listado del repo.
- `app/models/user.py`, `app/models/role.py`, `app/models/search.py`, etc. usan SQLAlchemy 2 async, pero sin revisión automática de índices FK en este informe.
- `app/repositories/*` usa sesiones async y consultas tipadas; separación de concerns correcta a nivel de estructura.

## No verificado / requiere ejecución que este entorno no permite
- `alembic upgrade head` desde DB vacía no se ejecutó porque no hay `alembic/` y no corresponde hacer migraciones contra prod sin respaldo previo.
- `alembic heads` no se ejecutó.

## Riesgos priorizados
| Riesgo | Severidad | Evidencia |
|---|---|---|
| Sin migraciones Alembic en el checkout | Alta | ausencia de `alembic/` |
| Potenciales FK sin índice | Media | no verificado |
| Scripts backup/restore no revisados | Media | no se encontraron en scope |
