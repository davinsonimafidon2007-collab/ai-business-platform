# Contexto de producto — uso personal (2026-08-07)

## Qué es esta app en la práctica

Herramienta **personal y local** para explorar importación de coches DE → ES:

- Búsqueda (sobre todo **AutoScout24**)
- Score, mercado, costes, ROI, oportunidades, negociación
- Frontend Next.js + API FastAPI en la máquina del usuario

**No** es un SaaS público ni un despliegue obligatorio en VPS.

## Infraestructura

| Opción | ¿Necesaria? |
|--------|-------------|
| PC local + Docker/venv + Postgres | Sí (uso normal) |
| VPS ~5 €/mes (Hetzner, netcup, etc.) | **No**, salvo querer jobs 24/7 con el PC apagado |
| Proxy residencial caro | **No** como plan base del MVP personal |
| Dominio / marca de correo | No obligatorio |

Un VPS de datacenter **no** sustituye un proxy residencial: mobile.de suele seguir respondiendo 403 a IPs de servidor.

## Fuentes de datos DE

| Fuente | Estado práctico |
|--------|-----------------|
| **AutoScout24** | Fuente fiable en vivo (parser `__NEXT_DATA__`) |
| **mobile.de** | 403 frecuente desde IPs datacenter/cloud; ToS restringen scraping automático |
| Fixtures ES / snapshots HTML | Desarrollo y tests sin golpear portales |

**No** diseñar la arquitectura alrededor de “comprar proxies para saltarse el anti-bot”.

- `MobileDeProvider` permanece **desacoplado** (scoring/ROI no dependen de él).
- A.5b (proxy live) queda **no prioritario** en uso personal.
- Si en el futuro hay **API/partner autorizado**, se cambia el provider sin rehacer el pipeline.

## Ops opcionales (credencial)

| Integración | ¿Obligatoria uso personal? |
|-------------|----------------------------|
| SMTP (alertas email) | No — sin SMTP la app hace log-only |
| Firebase (login Google) | No — basta auth email/password de la API |
| `PROVIDER_HTTP_PROXY` | No — solo si un día se insiste en mobile.de en vivo |

Comprobar estado: `python scripts/check_integrations_ready.py`  
(jwt/db deben READY; smtp/firebase/proxy pueden BLOCKED sin problema).

## Prioridad producto (personal)

1. Flujo local: search (AS24) → drawer (labels, cost_lines, coherence) → simulate → opportunities.
2. Checklist: `docs/E2E_MANUAL_CHECKLIST.md` (marcar fecha PASS cuando se ejecute).
3. SMTP/FIRE solo si el usuario los quiere.
4. mobile.de / proxy: aparcado.
5. Portales ES live: largo plazo; fixtures offline primero.

## Cronología reciente (resumen)

- Providers 1b, labels ROI/REC/SCORE, SEARCH.EMPTY, OPP labels.
- SIM.1 alineado con cost_lines/coherence; HEALTH.UI; ECON.2; SEARCH.PROVIDERS.1.
- E2E.MANUAL.1 + SMOKE.CRIT documentados.
- Decisión 2026-08-07: **uso personal, 0 € infra obligatoria, AS24-first, A.5b no prioritario.**

Ver también: `docs/HANDOFF_GROK_NEXT_SESSION.md`.

---

## Auth desactivada (PERSONAL.NOAUTH) — sin login obligatorio

La app funciona **sin registrarse ni iniciar sesión** con un flag (solo uso
personal). El código de auth (JWT, Firebase/Google, login/register) **no se
borra del repo**; queda desactivado por si lo quieres más adelante.

En local:

```env
AUTH_DISABLED=true
NEXT_PUBLIC_AUTH_DISABLED=true
```

Qué hace:

- Backend: `get_current_user` deja de mirar el Bearer y hace get-or-create del
  usuario local ADMIN (`local@localhost`, UUID fijo
  `00000000-0000-4000-8000-000000000001`) en la tabla `users` → FKs ok y
  `/admin` accesible.
- Frontend: no redirige a `/auth/login`, no exige token, no inicializa
  Firebase/Google y oculta el logout.
- Las rutas `/auth/*` y las páginas login/register siguen existiendo; nadie te
  obliga a entrar.

**No usar así en un despliegue público**: con el flag ON cualquiera que alcance
el puerto HTTP sería ADMIN sin contraseña. En un deploy real dejar `false`.

**`APP_MODE` no controla la auth.** Existe `APP_MODE=personal|multiuser` como
documentación de intención de producto, pero el único interruptor del bypass es
`AUTH_DISABLED`. Poner `APP_MODE=personal` sin `AUTH_DISABLED=true` mantiene el
login JWT normal.

**Producción bloqueada:** con `ENVIRONMENT=production` + `AUTH_DISABLED=true` la
app **no arranca** (fail-fast). Si aun así lo quieres (puerto no expuesto), hay
override explícito: `ALLOW_AUTH_DISABLED_IN_PROD=true`.

### TODO — PERSONAL.NOAUTH ✅ / PERS.CLOSE.1 ✅

- [x] `AUTH_DISABLED` + usuario local ADMIN (get-or-create en DB)
- [x] `get_current_user` bypass JWT con flag ON + middleware salta pre-auth
- [x] Front guard off + `NEXT_PUBLIC_AUTH_DISABLED` + store local user
- [x] Tests flag on/off
- [x] PERS.CLOSE.1: un solo camino en `get_current_user` (nunca `None`),
      fail-fast en production, home directa a `/dashboard`, docs alineadas

### Checklist manual (uso personal)

- [ ] Home → dashboard sin login
- [ ] Search no pide auth
- [ ] Opportunities lista (vacía o con datos) sin 401
- [ ] No hay botón de logout (o no rompe la sesión)

HANDOFF: auth opcional; personal → `AUTH_DISABLED=true`.

