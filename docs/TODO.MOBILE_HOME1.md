# TODO — MOBILE.HOME.1: dashboard móvil mockup ✅

Inicio tipo **Opción 3** composado en `frontend/src/app/dashboard/page.tsx` con
componentes presentacionales en `frontend/src/app/features/home/`. No se tocan
tokens (THEME.1 ya aplicado) ni se reabre el shell (SHELL.1). No backend nuevo:
se reutilizan las APIs existentes (search history, dashboard stats, opportunities).

- [x] Greeting + KPI cards
- [x] Teasers oportunidades / actividad
- [x] CTA Buscar
- [x] Empty/error ES
- [x] Skeletons + Retry (error de red no deja la home en blanco)
- [x] Desktop: grid 2 columnas (`md:grid-cols-2`), mismos bloques
- [x] `tsc --noEmit` OK

## Aceptación
- [x] `/dashboard` móvil: saludo + ≥2 KPIs en cards
- [x] CTA visible a búsqueda
- [x] Lista(s) oportunidades / actividad (o empty claro)
- [x] Sin sidebar en móvil (SHELL) + acento morado (THEME)
- [x] Error de red no deja la home en blanco (banner ES + “Reintentar”)
- [x] `tsc` OK, sin regresiones graves en desktop

## Componentes nuevos
- `src/app/features/home/HomeGreeting.tsx`
- `src/app/features/home/KpiRow.tsx`
- `src/app/features/home/HomeSection.tsx`
- `src/app/features/home/OpportunityTeaserCard.tsx`
- `src/app/features/home/RecentItemCard.tsx`

## Siguiente
- **MOBILE.SEARCH.1** — búsqueda full-screen + resultados en cards + detalle en stack.