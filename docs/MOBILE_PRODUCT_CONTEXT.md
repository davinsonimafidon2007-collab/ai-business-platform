# Contexto producto — Móvil first

## Prioridad
Frontend y UX de **app móvil** (Capacitor). El dueño usará sobre todo el teléfono.

## Referencia UI
Opción 3 — Elegante/Premium (morado): dashboard KPIs, cards, inspección por pasos,
detalle de fase, bottom navigation. No clonar el admin web con sidebar.

## Serie de tasks (orden)
1. MOBILE.NAV.1 — atrás Android in-app ✅
2. MOBILE.API.1 — API alcanzable desde el dispositivo ✅
3. MOBILE.SHELL.1 — bottom tabs + layout sin sidebar en móvil ✅
4. MOBILE.THEME.1 — tema morado premium ✅
5. MOBILE.HOME.1 — dashboard móvil (saludo, KPIs, actividad) ✅
6. MOBILE.SEARCH.1 — búsqueda full-screen + resultados en cards
7. MOBILE.INSPECT.1 — wizard inspección
…

## Tema (MOBILE.THEME.1) — aplicado
- THEME.1 aplicado — **primary = violet premium** (Opción 3).
- Tokens `primary-*` violeta en `globals.css` (500 = `#8b5cf6`, 600 = `#7c3aed`).
- Tab activo / header móvil alineados (morado + indicador).
- Desktop hereda el mismo design system (mismas clases `primary-*`).

## Shell (MOBILE.SHELL.1) — navegación tipo app
- Móvil / nativo (Capacitor): `AppShell` renderiza cabecera compacta, contenido a
  ancho completo y **bottom tabs** (`MobileTabBar`, 5 destinos). Sin `Sidebar`
  ni `pl-64`.
- Desktop (≥768px): se mantiene el `Sidebar` + `Navbar` clásico.
- Detección: `useIsMobile` (<768px o plataforma nativa Capacitor).
- `/more` agrupa los destinos que no caben en los tabs (vehículos, inspección,
  historial, API keys, admin).
- La paleta morada "Opción 3" (premium, cards) **no** se aplicó aquí: es la task
  **MOBILE.THEME.1**. Aquí solo la estructura.

## Home (MOBILE.HOME.1) — inicio tipo Opción 3 ✅
- `dashboard/page.tsx` compone el dashboard **móvil-first** con componentes
  presentacionales en `src/app/features/home/`:
  `HomeGreeting`, `KpiRow`, `HomeSection`, `OpportunityTeaserCard`,
  `RecentItemCard`.
- Estructura: saludo `¡Hola, {nombre}!` → cards KPI (grid 2-col móvil / 4-col
  desktop) → CTA brillante “Buscar vehículos” (`/search`) → 2 listas
  (Oportunidades destacadas + Actividad reciente) en stack vertical en móvil,
  grid 2 columnas en `md+`.
- Datos **sin backend nuevo**: reutiliza `useSearchHistory`, `useDashboardStats`
  y `fetchOpportunities({ limit: 5 })` (existentes). Nombre desde `useAuthStore`
  (`user.full_name` / email local).
- Estados: skeletons (4 KPI + 2 listas), error de red ES + “Reintentar”
  (invalidate queries), empty “Aún no hay oportunidades — busca un vehículo” +
  link a `/search`. Nunca pantalla en blanco.
- Sin sidebar en móvil (AppShell) y acento morado premium (THEME.1).

## No hacer en tasks móvil
- Reimplementar scrapers / proxy / SMTP salvo task explícita
- Tratar el front solo como “responsive desktop”

---

## API desde el dispositivo (MOBILE.API.1)

La app (Capacitor) y el navegador del PC hablan con la misma API. La URL se
inyecta **en build** vía `NEXT_PUBLIC_API_URL` (sin `/api/v1` al final; el
cliente axios en `src/app/services/api/client.ts` la concatena).

| Entorno | `NEXT_PUBLIC_API_URL` |
|---------|----------------------|
| Web PC (Chrome) | `http://127.0.0.1:8000` |
| Emulador Android | `http://10.0.2.2:8000` |
| Dispositivo real (misma WiFi) | `http://<IP-LAN-PC>:8000` |

### Regla de oro
- **Nunca** uses `127.0.0.1` / `localhost` dentro del APK en un teléfono real:
  apuntan al propio móvil, no al PC.
- El backend debe escuchar en `0.0.0.0`. `docker-compose.yml` ya lo hace
  (`uvicorn ... --host 0.0.0.0 --port 8000`, puerto `8000:8000`).
- El teléfono debe estar en la **misma WiFi** que el PC y el puerto `8000`
  abierto en el **firewall de Windows** en red privada.

### Cómo elegir la URL + rebuild (clave)
`NEXT_PUBLIC_*` se inyecta **en build**, no en runtime. Además, en Next.js
`frontend/.env.local` tiene **prioridad sobre** `frontend/.env.production`, así
que el target real es el que dejes **activo** en `.env.local`:

1. Edita `frontend/.env.local` dejando activa la línea que toque (Web/emulador/móvil).
2. Rebuild:
   ```powershell
   cd frontend
   npm run build            # regenera `out/` con la URL horneada
   npx cap sync android     # vuelca `out/` en el proyecto Android
   ```
3. Reinstala el APK en el dispositivo. El hot reload del navegador **NO**
   actualiza el APK.

### Verificación desde el móvil
Navegador Chrome del teléfono (misma WiFi):

```
http://<IP-LAN-PC>:8000/api/v1/health
```

Debe responder `{"status":"ok", ...}`. Si eso no carga → es red/firewall, no
React. Si carga pero la app da **Network Error** → revisar cleartext/CORS.

### Cleartext HTTP (Android)
Android 9+ bloquea HTTP salvo permiso. Permiso de desarrollo SOLO para los
hosts del backend local en
`frontend/android/app/src/main/res/xml/network_security_config.xml`
(`10.0.2.2`, `localhost` y el IP LAN actual). No usar cleartext en una
producción pública sin HTTPS.

### CORS
`CORS_ORIGINS` por defecto ya incluye `capacitor://localhost`,
`ionic://localhost`, `http://localhost` y `https://localhost`. Como
`capacitor.config.ts` usa `androidScheme: "http"`, el WebView manda
`Origin: http://localhost`, ya permitido. Dev personal: no hace falta tocar
nada. Nunca `*` en producción con credenciales.

### Convierte el IP LAN si cambia
`Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -like "192.168.*" }`.
Si cambia, actualiza `network_security_config.xml` y `frontend/.env.local`.