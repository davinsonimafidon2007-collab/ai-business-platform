# Auditoría — Backend / API
Fecha: 2026-08-20
Commit auditado: cc2a256a433d998531be578517b3abdaf1217996

## Hallazgos confirmados (con evidencia)
- `app/api/v1/users.py:42-47` — `get_user` usa `Depends(get_current_user)`, pero no valida que el `user_id` del path coincida con el usuario autenticado; un usuario autenticado puede consultar cualquier otro usuario por ID. Riesgo IDOR.
- `app/api/v1/users.py:52-57` — `update_user` igual: sin comprobación `current_user.id == user_id`.
- `app/api/v1/routes/search.py:258-261` — `POST /search` no usa `Depends(get_current_user)`, queda público sin autenticación.
- `app/api/v1/routes/vehicles.py:70-73` — `GET /vehicle/{provider}/{id}` no usa `Depends(get_current_user)`.
- `app/api/v1/dashboard.py:24-25` — `GET /dashboard/stats` no usa auth, expone métricas agregadas sin identidad.
- `app/api/v1/routes/inspection.py` — rutas sin `get_current_user`; cualquier sesión de inspección es accesible/modificable por quien conozca el `session_id`.
- `app/api/v1/routes/health.py` — endpoints públicos adecuados para `/health` y `/health/ready`.
- `tests/integration/api/test_health_api.py` existe; también hay tests para search, vehicle, auth, users, searches, inspection, security, rbac. No hay tests de integración para `dashboard/stats` ni para el flujo público de `/search`.

## No verificado / requiere ejecución que este entorno no permite
- Ejecución real de `pytest`/testclient contra los endpoints sin auth para confirmar status codes 200/401 en vivo.

## Riesgos priorizados
| Riesgo | Severidad | Evidencia |
|---|---|---|
| IDOR en `/users/{user_id}` y PATCH `/users/{user_id}` | Alta | `app/api/v1/users.py:42-57` |
| `/search` público | Alta | `app/api/v1/routes/search.py:258` |
| `/vehicle/{provider}/{id}` público | Media | `app/api/v1/routes/vehicles.py:70` |
| Dashboard sin auth | Media | `app/api/v1/dashboard.py:24` |
| Inspecciones sin ownership/auth | Alta | `app/api/v1/routes/inspection.py:37-61` |
| Sin test de integración para `/dashboard/stats` | Media | ausente en `tests/integration/` |
