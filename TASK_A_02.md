# TASK_A_02 — Evitar IDOR en /users/{user_id}

## Problema
`app/api/v1/users.py` permite a un usuario autenticado consultar/editar
cualquier usuario por `user_id` sin comprobar que es el mismo.

## Archivos a modificar
- `app/api/v1/users.py`

## Accion
- En `get_user` y `update_user`, comparar `current_user.id == user_id` o
  comprobar `require_admin` cuando corresponda.
- Fallar con 403/404 segun politica.

## Criterio de aceptacion
- Un usuario normal solo accede/edita su propio recurso.
- Admin mantiene acceso completo.
