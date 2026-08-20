# Auditoría — Mobile / Capacitor
Fecha: 2026-08-20
Commit auditado: cc2a256a433d998531be578517b3abdaf1217996

## Hallazgos confirmados (con evidencia)
- `frontend/android/` no existe en este checkout.
- `frontend/src/app/services/google-auth.ts`, `frontend/src/app/config/`, `frontend/build-android*`, `frontend/full-build.bat` no existen en el listado del repo.
- `package.json` no contiene scripts de build Android/Capacitor.
- Sin `google-services.json` hallado en árbol.
- Sin logs `*.txt`/`*.log` rastrados en scope.

## No verificado / requiere ejecución que este entorno no permite
- Pipeline APK real, inyección de `NEXT_PUBLIC_*`, existencia y uso de `google-services.json`.

## Riesgos priorizados
| Riesgo | Severidad | Evidencia |
|---|---|---|
| Proyecto mobile ausente en checkout | Alta | no existe `frontend/android/` ni scripts mobile |
| Sin `google-services.json` confirmado | Alta | no hallado |
| Variables `NEXT_PUBLIC_*` no auditables | Alta | archivos no presentes |
