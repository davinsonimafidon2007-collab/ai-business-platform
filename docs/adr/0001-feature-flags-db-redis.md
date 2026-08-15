# ADR-001: Feature flags gestionados por DB + Redis

- Estado: Aceptado
- Fecha: 2026-08-15
- Área: Configuración dinámica / Operabilidad

## Contexto

El sistema necesita activar/desactivar funcionalidades (fixtures, proveedores,
canary, migraciones) sin redeploy. Opciones:
settings de entorno, flags en DB, cache en proceso, Redis.

## Decisión

Flags persistidos en BD (`feature_flags`) con lectura cacheada en Redis (TTL
60s) y fallback a DB + write-back. API admin CRUD protegida por `require_admin`.
`app/services/feature_flag_service.py`.

## Justificación

- Persistencia portable (SQLite/Postgres) y consultable.
- Redis con `decode_responses=True` da latencia baja y simple TTL; la caída de
  Redis degrada a DB sin romper (fail-soft).
- Admin puede togglear sin entorno, útil para despliegue personal (AUTH_DISABLED).

## Consecuencias

- El cache usa TTL 60s; cambios tardan hasta 1 min en propagarse en toda la app.
- Invalidación explícita en `set_flag`/`delete_flag` para lectura inmediata.

## Alternativas

- Environment only: requiere redeploy por cambio.
- Con el cache en proceso: no se comparte entre réplicas.