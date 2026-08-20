# Auditoría — Frontend web
Fecha: 2026-08-20
Commit auditado: cc2a256a433d998531be578517b3abdaf1217996

## Hallazgos confirmados (con evidencia)
- `frontend/package.json:11-13` — scripts de test actuales: `test`, `test:run`, `test:coverage` usan Vitest. No existe `test:e2e` ni dependencia de Playwright declarada.
- `frontend/package.json:34-49` — devDependencies sin `@playwright/test` ni `playwright` instalados en este checkout.
- `frontend/next.config.ts` — solo define `outputFileTracingRoot: __dirname`. No se encontró incompatibilidad `output: export` + `next start`; no está configurado `output`.
- `frontend/vitest.config.ts` existe; cobertura con Vitest está presente en scripts.
- Rutas/datos de mercado ES desde frontend: **NO VERIFICADO** por falta de carpetas `(dashboard)` y componentes consumidores en el listado del checkout; el scope no mostró páginas adicionales más allá de `frontend/src/` superficial.

## No verificado / requiere ejecución que este entorno no permite
- Estados loading/error/empty state página por página porque no se localizaron las páginas de mercado ES en `frontend/src/` dentro del listado examinado.
- Ejecución real de tests e2e en CI.

## Riesgos priorizados
| Riesgo | Severidad | Evidencia |
|---|---|---|
| Sin Playwright configurado para e2e web | Media | `frontend/package.json` |
| No se confirmaron estados UI de mercado ES | Media | no hallado en scope de `frontend/src/` |
| Incompatibilidad `output: export` no confirmada | Baja | `frontend/next.config.ts` no usa `output` |
