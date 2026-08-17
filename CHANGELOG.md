# Changelog

## [v1.0.0] - 2026-08-17

### Añadido
- **Bloque 1**: Configuración de cobertura al 85% (Vitest), PWA con manifest y service worker.
- **Bloque 2**: Tests unitarios para stores (auth, vehicle), servicios (google-auth, api/client) y hooks (use-hydrated).
- **Bloque 3**: Playwright E2E, exclusiones de Capacitor, cobertura de branches SSR.
- **Bloque 4**: Health check visual, toasts de errores, skeletons para listado y detalle.
- **Bloque 5**: Documentación (README, CONTRIBUTING) y limpieza de código muerto.

### Mejorado
- Cobertura frontend: de ~72% a ≥85% en todas las métricas.
- Manejo de errores con sonner toasts.
- Experiencia de usuario con skeletons y feedback visual.

### Corregido
- Error de `use-hydrated.ts` (contenía código Python).
- Errores de tipo en `analytics.ts` (`as never` para satisfacer overload).
- Conflictos de merge con `origin/main`.

### Eliminado
- Código comentado y dependencias obsoletas.