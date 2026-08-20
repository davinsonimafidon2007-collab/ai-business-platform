# TASK_A_01 — Añadir auth a rutas sensibles sin proteccion

## Problema
`/search`, `/vehicle/{provider}/{id}`, `/dashboard/stats` y rutas de inspección
no exigen `Depends(get_current_user)`, exponiendo lógica de negocio y datos
de proveedores sin identidad.

## Archivos a modificar
- `app/api/v1/routes/search.py`
- `app/api/v1/routes/vehicles.py`
- `app/api/v1/dashboard.py`
- `app/api/v1/routes/inspection.py`

## Accion
- Inyectar `current_user=Depends(get_current_user)` en cada endpoint sensible.
- Rechazar peticiones sin auth con 401 automatico desde la dependencia.
- Para inspecciones, validar ownership por `session_id/user_id` en servicio.

## Criterio de aceptacion
- Todos los endpoints sensibles devuelven 401 sin token.
- `/health` y `/health/ready` siguen publicas.
