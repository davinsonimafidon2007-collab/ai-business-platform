# E2E manual — camino crítico (E2E.MANUAL.1)

**Fecha:** YYYY-MM-DD  
**Entorno:** local / staging  
**Tester:**  
**Build / commit:**  

## 0. Preflight

| # | Paso | PASS |
|---|------|------|
| 0.1 | `python scripts/check_integrations_ready.py` — jwt/db READY (smtp/firebase/proxy pueden BLOCKED) | ☐ |
| 0.2 | `python scripts/smoke_es_providers.py` exit 0 | ☐ |
| 0.3 | `python scripts/release_check.py --skip-smoke` PASSED | ☐ |
| 0.4 | API up (`/health` o `/api/v1/health` responde 200 en http://localhost:8000) | ☐ |
| 0.5 | Frontend up (página login visible en http://localhost:3000/auth/login) | ☐ |

## 1. Auth

| # | Paso | Esperado | PASS |
|---|------|----------|------|
| 1.1 | Register o login email/password en http://localhost:3000/auth/login | 200, tokens, redirección a app | ☐ |
| 1.2 | Ruta protegida sin token (ej. http://localhost:3000/opportunities) | redirect login o 401 API | ☐ |
| 1.3 | (Opcional) Google login | Solo si FIREBASE configurado; si no, anotar SKIP | ☐ / SKIP |

## 2. Search → resultados

Abrir http://localhost:3000/search/ y ejecutar query.

| # | Paso | Esperado | PASS |
|---|------|----------|------|
| 2.1 | Search query válida (ej. BMW) + provider AS24 o default | Lista con ≥1 resultado o empty state ES claro | ☐ |
| 2.2 | Query absurda / sin hits | Empty state en **español** + hint Admin/providers (SEARCH.EMPTY.1) | ☐ |
| 2.3 | Error de red (API caída) | Mensaje error ES, no stack crudo | ☐ |

## 3. Drawer (vehículo)

Abrir un resultado con market + profit + opportunity si el pipeline lo rellena.

| # | Paso | Esperado | PASS |
|---|------|----------|------|
| 3.1 | **Explanation** de mercado visible (MKT.2) | Texto ES no vacío si hay comparables | ☐ |
| 3.2 | **Fuentes** (`provider_sources`) | Chips o lista (MKT.3) | ☐ |
| 3.3 | **Score** | `category_label_es` (SCORE.1), no solo código EN | ☐ |
| 3.4 | **Profit / cost_lines** | Partidas con `label_es` (PROFIT.1) | ☐ |
| 3.5 | **coherence_warnings** | Si el caso es extremo, avisos; si normal, ausentes o lista vacía (ROI.1) | ☐ |
| 3.6 | **Recomendación / riesgo** | `*_label_es` (REC.1) | ☐ |
| 3.7 | **Negociación** | Secciones Apertura / defectos / mercado / Cierre en ES (NEG.1) | ☐ |

## 4. Opportunities

Navegar a http://localhost:3000/opportunities (o ruta real del listado).

| # | Paso | Esperado | PASS |
|---|------|----------|------|
| 4.1 | Listado `/opportunities` | Items con labels ES de rec/riesgo (OPP.LIST.1) | ☐ |
| 4.2 | Vacío | Empty ES aceptable | ☐ |

## 5. Admin

Usuario **ADMIN**. Navegar a http://localhost:3000/admin.

| # | Paso | Esperado | PASS |
|---|------|----------|------|
| 5.1 | Admin status — bloque **Providers** | `registered` + flags + perfil (ADMIN.1b) | ☐ |
| 5.2 | Health compuesto | `checks.api` / `database` / `redis` coherentes (ok o degraded si Redis off) | ☐ |

## 6. Cierre

| Resultado global | ☐ PASS total / ☐ PASS con SKIP (Firebase/proxy) / ☐ FAIL |
| Notas | |
| Capturas (opcional) | rutas o archivos locales, **no** secretos |

## Fuera de este checklist

- mobile.de live (A.5b), SMTP real, Firebase SA, AS24-ES live.
- Playwright/Cypress (task futuro TEST.E2E.1).
