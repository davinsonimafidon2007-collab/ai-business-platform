=== AUDITORÍA FRONTEND WEB (AGENTE 2) ===
Fecha: 2026-08-20
Directorio auditado: frontend/

--- ARCHIVOS LEÍDOS CON EVIDENCIA ---

1. CONFIGURACIÓN Y ENTORNO
- frontend/package.json: existe, define scripts build/test/lint.
- frontend/.env.example: existe (líneas 1-35) con NEXT_PUBLIC_API_URL, CAPACITOR_ANDROID_SCHEME, NEXT_PUBLIC_AUTH_DISABLED, Firebase vars (vacías), Google Client IDs (vacías).
- frontend/.env.local: NO EXISTE (verificado con Test-Path).
- frontend/next.config.ts: output="export", images unoptimized, headers de seguridad (X-Content-Type-Options, X-Frame-Options, Referrer-Policy), webpack split chunks (vendor/firebase), alias lodash→lodash-es.
- frontend/tsconfig.json / tsconfig.vitest.json: presentes.
- frontend/vitest.config.ts: cobertura acotada a store/** y services/** (excluye client.ts), umbrales bajos (30/30/20/30).

2. SERVICIOS API / CONEXIÓN REAL CON BACKEND
- frontend/src/app/services/api/client.ts (178 líneas): Cliente axios con baseURL = getApiBaseUrl() + "/api/v1". Interceptores: request (agrega Bearer token), response (retry con backoff exponencial + jitter, refresh token 401, redirección a login). Método isRetryable comprueba 429 y >=500 para métodos idempotentes (get/head/delete/options). Refresh token hace POST a /api/v1/auth/refresh. Maneja authDisabled para evitar loop 401. RETRY_MAX_ATTEMPTS=2, RETRY_BASE_DELAY_MS=500, RETRY_MAX_DELAY_MS=4000.
- frontend/src/app/services/api/index.ts: wrappers apiGet, apiPost, apiPatch, apiDelete (no manejan errores adicionales, solo pasan a axios).
- frontend/src/app/services/api/storage-cache.ts: caché localStorage con clave versionada (CACHE_VERSION="v1"), TTL por defecto 1h. Funciones: cacheGet, cacheSet, cacheIsExpired, cacheRemove, cacheClearAll, subscribeToCacheChanges. Silenciosa ante errores.
- frontend/src/app/config/api-url.ts: Resolución jerárquica: override localStorage (api_base_url), NEXT_PUBLIC_API_URL (env), Android nativo (10.0.2.2:8000), localhost/127.0.0.1 con puerto 8000, fallback http://localhost:8000. setApiBaseUrl guarda en localStorage.
- frontend/src/app/config/app-mode.ts: No leído directamente, pero referenciado en api/client.ts y auth-guard.ts para isAuthDisabled.
- frontend/src/app/types/api.ts: interfaces ApiResponse, PaginatedResponse, ApiError.

3. SERVICIOS DE NEGOCIO (REAL / MOCK EN TESTS)
- frontend/src/app/services/opportunities.ts: fetchOpportunities (GET /opportunities con params). Real, usa api.
- frontend/src/app/services/search.ts: searchService (searchVehicles POST /search, getSearchHistory GET /searches, getSearchById GET /searches/{id}, deleteSearch DELETE /searches/{id}, saveSearchToHistory POST /searches con payload construido, getDashboardStats GET /dashboard/stats, getStaticBrandsAndModels con caché localStorage 24h). Real, usa api; marcas/modelos estáticos son datos locales (no vienen del backend).
- frontend/src/app/services/deals.ts: fetchDeals, createDeal, updateDealStatus, updateDealSimulation. Real, usa api.
- frontend/src/app/services/health.ts: fetchHealth (GET /health), captura 503 y devuelve respuesta con datos. Real.
- frontend/src/app/services/dashboard.ts, adminMetrics.ts, adminStatus.ts, analytics.ts, featureFlags.ts, google-auth.ts, inspection.ts, offline-queue.ts, push-notifications.ts, storage.ts: no leídos a detalle, pero existen en directorio.

4. HOOKS
- frontend/src/app/hooks/useNetworkStatus.ts: detecta online/offline, expone status "online" | "offline" | "unknown". Tiene offlineFetch para fallback a stale data.
- frontend/src/app/hooks/useApiError.ts: parseApiError (maneja Response y Error), getStatusMessage por código de estado, handleApiError (muestra toast), isRetryableError.
- frontend/src/app/hooks/use-cached-query.ts: no leído completo, pero test existe (use-cached-query.test.tsx) y referencia storage-cache.
- frontend/src/app/hooks/use-search.ts: referencia en dashboard (useSearchHistory, useDashboardStats), no leído completo.
- frontend/src/app/hooks/use-opportunities.ts, useOpportunityDetail.ts, useAgents.ts, etc.: presentes pero no auditados línea por línea. Se asume que consumen servicios correspondientes.
- frontend/src/app/hooks/use-app-update.ts, use-rate-limit.ts, use-deep-links.ts, notification-navigation.ts, use-service-worker.ts, use-offline.tsx, use-onboarding.tsx, useIsMobile.ts, use-biometric.tsx, useAndroidBackButton.ts, use-logout.ts, use-opportunities.ts, use-opportunity-detail.ts: presentes.

5. COMPONENTES UI (ACCESIBILIDAD / UX)
- frontend/src/app/components/ui/data-states.tsx: LoadingState (spinner + mensaje), ErrorState (título, mensaje, botón Reintentar), DataStateEmptyState (icono, título, descripción, acción opcional), SkeletonRow / SkeletonList, DataState (wrapper que decide qué mostrar según isLoading/isError/data). Usa aria-hidden en Skeleton (linea 13). No usa aria-live para estados de carga/error.
- frontend/src/app/components/ui/EmptyState.tsx: icono, título, descripción, acción (Link o button). Usa Link con href y className, no aria-label explícito en botón de acción (depende del texto visible).
- frontend/src/app/components/ui/ErrorDisplay.tsx: clasifica errores por mensaje (401, 403, network, 500, etc.). Muestra título, detalle, hint opcional, botón Reintentar. No usa aria-live.
- frontend/src/app/components/ui/button.tsx: componente Button con variant, size, focus-visible ring, disabled styles. No tiene aria-label por defecto (depende de props extendidas).
- frontend/src/app/components/ui/input.tsx: Input con label asociado a htmlFor=id, mensaje de error, estados focus y disabled. Usa label visible, accesible básico.
- frontend/src/app/components/ui/Skeleton.tsx: Skeleton, SkeletonRow, SkeletonCard. Skeleton tiene aria-hidden="true" (linea 13). No tiene aria-busy ni aria-label.
- frontend/src/app/components/ui/ScoreBadge.tsx: no leído completo.
- frontend/src/app/components/ui/Toast.tsx, ToastProvider.tsx, ToastContainer.tsx: sistema de toasts, no auditados a detalle.
- frontend/src/app/components/ui/app-update-banner.tsx, rate-limit-toast.tsx: presentes.
- frontend/src/app/components/ui/Pagination.tsx: botones anterior/siguiente con disabled, números de página, no usa aria-label explícito en cada botón (solo texto visible).

6. NAVEGACIÓN / LAYOUT
- frontend/src/app/layout.tsx: html lang="es", suppressHydrationWarning, metadata básica, viewport con themeColor (morado premium). No hay manifest PWA ni service-worker registrado en HTML.
- frontend/src/app/layout/AppShell.tsx: detecta móvil (useIsMobile), renderiza cabecera compacta + contenido + MobileTabBar en móvil; Sidebar + Navbar en desktop. Usa useIsMobile para detección.
- frontend/src/app/layout/sidebar.tsx: navegación fija con items (Dashboard, Búsqueda, Vehículos, Oportunidades, Deals, Inspección, API keys, Historial, Admin para ADMIN). Usa aria-label en Link de Configuración (linea 27). No usa aria-current en items activos (solo clases CSS).
- frontend/src/app/layout/navbar.tsx: header sticky con título, botón notificaciones (sin aria-label explícito en línea 34), botón tema (aria-label="Toggle theme"), botón logout (texto visible o icono svg sin aria-label en línea 57-61). El botón de notificaciones no tiene aria-label o texto visible (solo svg, línea 34-38), lo que lo hace inaccesible para lectores de pantalla.
- frontend/src/app/layout/MobileTabBar.tsx: nav con aria-label="Navegación principal", 5 tabs, aria-current cuando activo, aria-hidden en iconos. Badge de resultados nuevos visible. Accesible básico.

7. PÁGINAS (PÁGINAS REALES, NO MOCK EN CÓDIGO)
- frontend/src/app/page.tsx: no leído, probablemente redirección.
- frontend/src/app/(app)/dashboard/page.tsx (líneas 1-299): página real que consume useSearchHistory, useDashboardStats, fetchOpportunities, fetchHealth, useNetworkStatus, useAuthStore. Incluye estados de carga (RowSkeleton), error (ErrorDisplay), vacío (EmptyOpportunities, EmptyActivity), offline (banner gris), backend down (banner ámbar con link a Configuración). No es mock; consume datos reales del backend a través de hooks y queries.
- frontend/src/app/auth/login/page.tsx y register/page.tsx: páginas que envuelven features/auth/login-page.tsx y register-page.tsx. Real.
- frontend/src/app/features/auth/login-page.tsx (líneas 1-163): formulario con react-hook-form + zod resolver (email, password, confirmPassword). Llama a api.post("/auth/login"), api.get("/auth/me"), persiste sesión con useAuthStore.setSession. Muestra error de red (setError). No usa loading/error/empty states formales, solo setIsLoading y mensaje de error simple.
- frontend/src/app/features/auth/register-page.tsx (líneas 1-180): similar, con esquema de confirmación de contraseña. Real.
- frontend/src/app/(app)/search/page.tsx, opportunities/page.tsx, deals/page.tsx, etc.: no leídos completos, pero existen y se asume que consumen servicios.

8. COMPONENTES DE FEATURE (OPORTUNIDAD, VEHÍCULO, INSPECCIÓN)
- frontend/src/app/components/opportunities/OpportunityCard.tsx (líneas 1-82): Link con imagen (next/image), alt={title}, datos de oportunidad. Usa Image de Next.js con alt, accesible básico.
- frontend/src/app/components/opportunity/AgentResult.tsx (líneas 1-45): presenta análisis del agente con confianza, recomendación, datos clave. Usa aria-hidden en Sparkles (linea 43) y CheckCircle2 no usado. No usa aria-live para cambios dinámicos.
- frontend/src/app/components/opportunity/ActivityLog.tsx, ApprovalActions.tsx, GeneratedFiles.tsx, HumanSupervision.tsx, PhaseTimeline.tsx, RequestChangesModal.tsx, ApprovalDetailDrawer.tsx, ApprovalReviewCard.tsx, OpportunityDetailClient.tsx: presentes, no auditados línea por línea.
- frontend/src/app/features/home/OpportunityTeaserCard.tsx, RecentItemCard.tsx: cards con Link, aria-hidden en iconos (ChevronRight, Sparkles, History), sin aria-label en el link completo (el texto visible hace la función, accesible básico).
- frontend/src/app/features/inspection/InspectionPage.tsx, InspectionProgressBar.tsx, CategoryStep.tsx, InspectionSummary.tsx, LiveNegotiationPanel.tsx: presentes, no auditados en detalle.
- frontend/src/app/features/search/SearchFilters.tsx (líneas 1-317): formulario de búsqueda con inputs (label + htmlFor), selects, button con aria-label. Usa React.FormEvent, no react-hook-form. Accesible básico completo (labels visibles, aria-label en botones, aria-expanded/aria-controls en botón "Más filtros").

9. PWA / SERVICE WORKER / MANIFEST
- frontend/public/service-worker.js (líneas 1-147): Service Worker con caché "abp-cache-v1", precache de rutas estáticas (/dashboard/, /opportunities/, /search/, /), patrón de caché para API GET (opportunities, deals, searches, dashboard) con stale-while-revalidate, fallback 503 offline sin caché. Background sync para "sync-favorites" (IndexedDB). No hay registro del SW en layout (no se ve registro en layout.tsx o providers). El archivo existe en public/ pero no hay evidencia de que se registre (no hay código de registro en los archivos leídos).
- frontend/capacitor.config.ts: no leído completo, pero existe y referencia androidScheme.
- frontend/android/app/src/main/res/xml/network_security_config.xml: permite cleartext para localhost, 10.0.2.2, y IP LAN.
- frontend/android/app/src/main/AndroidManifest.xml: no leído, pero existe.
- frontend/.well-known/assetlinks.json: presente para verificación de Android App Links.
- No hay manifest.json en frontend/public/ (verificado con glob). No hay iconos PWA definidos. No hay registro de service worker en el código de React leído (no aparece en layout o providers).

10. ACCESIBILIDAD (FALTANTES ENCONTRADAS)
- frontend/src/app/layout/navbar.tsx línea 34: botón de notificaciones sin aria-label ni texto visible (solo svg). Inaccesible.
- frontend/src/app/components/ui/data-states.tsx: SkeletonRow y SkeletonList no usan aria-busy ni aria-label para indicar que es contenido cargando.
- frontend/src/app/components/ui/ErrorDisplay.tsx: no usa aria-live="assertive" o aria-live="polite" para notificar errores a lectores de pantalla.
- frontend/src/app/components/ui/EmptyState.tsx: no usa aria-live para notificar estado vacío.
- frontend/src/app/components/opportunity/AgentResult.tsx: no usa aria-live para cambios en recomendación.
- frontend/src/app/components/ui/Pagination.tsx: botones anteriores/siguientes no tienen aria-label (dependen del contexto visual).
- frontend/src/app/layout/sidebar.tsx: no usa aria-current en links activos (solo clase CSS).
- frontend/src/app/components/auth/auth-guard.tsx: carga con spinner simple sin aria-busy.
- No hay skip-to-content ni land marks (main, nav, aside) en todos los componentes; AppShell usa <main>, sidebar usa <aside>, MobileTabBar usa <nav> con aria-label, Navbar usa <header>. Accesible básico a nivel estructural.

11. FORMULARIOS
- frontend/src/app/features/auth/login-page.tsx: react-hook-form + zod resolver, validación en cliente (email, password min 8). No hay validación de red (catch sin detalle del error, solo "Credenciales inválidas").
- frontend/src/app/features/auth/register-page.tsx: react-hook-form + zod resolver, validación de confirmación de contraseña (refine). No hay feedback de errores del backend más allá de mensaje genérico.
- frontend/src/app/features/search/SearchFilters.tsx: formulario manual con useState, sin validación de esquema (solo inputs numéricos/texto). No usa react-hook-form ni zod.
- frontend/src/app/components/ui/input.tsx: componente base con label y error. No tiene required ni aria-required.

12. TESTS
- frontend/src/__tests__/setup.ts: solo importa @testing-library/jest-dom.
- frontend/src/__tests__/components/auth-guard.test.tsx (líneas 1-77): 3 casos (loading, redirección, autenticado). Mock de useRouter, usePathname, useAuthStore.
- frontend/src/__tests__/components/button.test.tsx, ScoreBadge.test.tsx, skeleton.test.tsx: presentes, no leídos completos.
- frontend/src/__tests__/hooks/use-cached-query.test.tsx (líneas 1-136): 4 casos, cubre caché, persistencia, revalidación, flag isBackgroundRefreshing.
- frontend/src/__tests__/hooks/use-logout.test.tsx, use-search.test.tsx, mobile/mobile-integration.test.ts, release/*: presentes.
- frontend/src/__tests__/services/api/client.test.ts (líneas 1-120): test de retry con mock de axios (mock create, mock instance, responseHandler). Verifica retry de errores de red, 503 con éxito en primer retry, no retry de 4xx excepto 401, no retry de métodos no idempotentes (post), y que expone axios instance. Usa process.env.NEXT_PUBLIC_AUTH_DISABLED = "true" para evitar loop de refresh.
- frontend/src/__tests__/services/deals.test.ts, opportunities.test.ts, search.test.ts, health.test.ts, adminStatus.test.ts, adminApiKeys.test.ts, apiKeys.test.ts, storage-cache.test.ts, simulateProfit.test.ts, offline-queue.test.ts: presentes. Todos usan vi.mock del cliente api.
- frontend/src/__tests__/store/auth-store.test.ts (líneas 1-133): cubre setSession, initialize con token válido/expirado, logout, decodeJwtPayload, getTokenExpiry.
- frontend/src/__tests__/store/theme-store.test.ts: presente.
- Cobertura configurada en vitest.config.ts: solo store/** y services/** (excluye api/client.ts). Umbral 30% líneas, funciones, 20% ramas, 30% declaraciones. Es un umbral muy bajo, lo que indica que la cobertura real de UI/páginas es baja o nula.

13. DOCS RELACIONADOS CON FRONTEND
- docs/MOBILE_PRODUCT_CONTEXT.md: explica prioridades móvil-first, shell con bottom tabs, dashboard móvil (KPI cards, CTA), uso de APIs existentes, sin backend nuevo, accesibilidad básica mencionada pero no verificada en detalle.
- docs/TODO.MOBILE_HOME1.md: checklist de tasks completados (greeting, KPI, teasers, CTA, empty/error, skeletons, retry). Todo marcado como completado.
- docs/BUILD.md: guía de build Android con Capacitor, requisitos, variables de entorno (NEXT_PUBLIC_API_URL, NEXT_PUBLIC_AUTH_DISABLED, Firebase vars, Google Client IDs), pasos de build (debug/release), verificación post-build (typecheck, lint, test, APK, splash, conexión).
- docs/firebase_setup.md, docs/PROXY_MOBILE_DE.md, docs/CONTEXT_PERSONAL_USE.md, docs/HANDOFF_GROK_NEXT_SESSION.md: presentes, no auditados a detalle.

--- QUÉ FUNCIONA ---

- Configuración de build (next.config.ts) con seguridad básica (headers), export estático, alias webpack, split chunks.
- Cliente API (client.ts) con retry exponencial, refresh token, manejo de 401, autodesactivación de auth (isAuthDisabled), timeout 30s.
- Resolución de URL de backend jerárquica (api-url.ts) con override en localStorage para móvil físico.
- Servicios de negocio (opportunities, deals, search, health) conectan con endpoints reales del backend (no son mock en producción).
- Hooks de red (useNetworkStatus) y error (useApiError) funcionan para UX de conectividad y mensajes.
- Dashboard (dashboard/page.tsx) usa datos reales (search history, stats, opportunities, health), maneja estados de carga (skeleton), error (ErrorDisplay), vacío (EmptyOpportunities/EmptyActivity), offline (banner), backend down (banner con link a Configuración).
- Componentes UI reutilizables (LoadingState, ErrorState, EmptyState, Skeleton, DataState) permiten estados consistentes.
- Navegación móvil (MobileTabBar) y desktop (Sidebar + Navbar) funcionan con detección de dispositivo.
- Formulario de login y registro con validación Zod (email, contraseña, confirmación) y manejo básico de errores.
- AuthGuard protege rutas con redirección a login cuando no hay autenticación (salvo authDisabled).
- Service Worker (service-worker.js) existe con estrategia de caché para API GET y assets estáticos.
- Tests unitarios existen para servicios, store, hooks críticos (auth-store, api client retry, use-cached-query, auth-guard, deals, search, opportunities).
- Layout base (layout.tsx) define lang="es", metadata, viewport con themeColor, y usa Providers (React Query, Toast, OfflineBanner).
- Páginas y componentes principales no usan datos simulados/mock en código fuente (consumen servicios reales); los mocks solo aparecen en archivos de test.

--- QUÉ ES MOCK / SIMULADO ---

- Todos los datos consumidos por los servicios en tests son mock (vi.mocked(api.get/post/patch/delete/resolvedValue/rejectedValue)). Esto es esperado para tests unitarios.
- frontend/src/app/services/search.ts: `getStaticBrandsAndModels` devuelve datos estáticos locales (Audi, BMW, Mercedes, etc.) con caché de 24h en localStorage. No consume backend (simulado/local).
- frontend/src/app/components/opportunity/AgentResult.tsx: recibe datos como props (confidence, suggestion, explanation, keyData). El componente solo presenta datos que vienen del padre; no consume API directamente. Es un componente presentacional (simulado en el sentido de que no hace fetch).
- frontend/src/app/components/ui/data-states.tsx: los componentes LoadingState, ErrorState, EmptyState son presentacionales; reciben props y no consumen datos por sí mismos. No son mock, pero son wrappers de presentación.
- frontend/src/app/features/home/HomeGreeting.tsx, KpiRow.tsx, OpportunityTeaserCard.tsx, RecentItemCard.tsx: presentacionales, reciben props del padre (dashboard/page.tsx).
- frontend/src/app/components/auth/auth-guard.tsx: usa useAuthStore (store global) y useRouter; no hace llamada a API, solo lee estado del store.
- frontend/src/app/store/auth-store.ts: usa secureStorage (localStorage o Capacitor Preferences) para persistir tokens; no hace llamadas HTTP directamente.
- `docs/MOBILE_PRODUCT_CONTEXT.md` y `docs/TODO.MOBILE_HOME1.md` mencionan funcionalidades "completadas" (checklist marcado), pero no hay evidencia de pruebas automatizadas de UI (tests de integración) que verifiquen que el dashboard móvil realmente carga datos en un dispositivo físico.
- `frontend/src/app/services/api/storage-cache.ts`: es una caché local que puede devolver datos viejos si no se refresca; no es un mock intencional, pero puede presentar datos desactualizados sin indicarlo claramente al usuario (excepto por el flag de offline en el dashboard).

--- QUÉ ESTÁ ROTO / DEFECTUOSO ---

- frontend/src/app/layout/navbar.tsx línea 34: botón de notificaciones sin `aria-label` ni texto visible. Inaccesible para lectores de pantalla y usuarios con solo teclado (aunque es un botón, no se sabe su función sin contexto visual).
- frontend/src/app/components/ui/ErrorDisplay.tsx: no usa `aria-live` para notificar errores. Un usuario con lector de pantalla puede no enterarse del mensaje de error cuando aparece dinámicamente.
- frontend/src/app/components/ui/data-states.tsx: `SkeletonRow` y `SkeletonList` no usan `aria-busy` ni `aria-label`. Un lector de pantalla no sabe que es contenido cargando.
- frontend/src/app/components/ui/EmptyState.tsx: no usa `aria-live`. Un usuario con lector de pantalla puede no notar que apareció un estado vacío.
- frontend/src/app/components/ui/Pagination.tsx: botones de navegación (`ChevronLeft`, `ChevronRight`) sin `aria-label`. Solo se ve un icono; sin contexto visual no se entiende la acción.
- frontend/src/app/feature/auth/login-page.tsx líneas 69-74: `catch` captura cualquier error sin distinguir entre red (no hay backend), 401, 500, etc. El mensaje es siempre "Credenciales inválidas", lo que es engañoso si el error es de red o del servidor.
- frontend/src/app/feature/auth/register-page.tsx líneas 78-82: similar, mensaje genérico "No se pudo crear la cuenta. Prueba con otro email." sin distinguir errores.
- frontend/src/app/services/search.ts línea 84-103: `getStaticBrandsAndModels` usa datos estáticos locales con caché de 24h. Si el backend actualiza las marcas/modelos disponibles, el frontend no se entera hasta que expire el caché o se borre manualmente. No hay mecanismo de invalidación remota.
- frontend/src/app/layout/AppShell.tsx: `MobileTabBar` está siempre visible en móvil, pero no hay forma de ocultarlo si el usuario está en una página que requiere más espacio (ej. inspección paso a paso). No hay prop para ocultar el tab bar.
- frontend/src/app/services/api/client.ts línea 20: `RETRYABLE_METHODS` incluye `delete` y `options`, que son idempotentes, pero `post` no está incluido, lo cual es correcto para mutaciones; sin embargo, el retry solo aplica a errores sin respuesta (`!error.response`) o 429/5xx, no a errores de red en POST, lo que podría ser un problema si una mutación necesita reintento (aunque no es idempotente).
- No hay registro del Service Worker (`service-worker.js`) en el código de React leído (`layout.tsx`, `providers.tsx`, `page.tsx` no registran el SW). El archivo existe en `public/` pero no hay evidencia de que se active en el navegador o en Capacitor.
- No hay `manifest.json` en `frontend/public/`. Esto impide que la app sea instalable como PWA en navegadores que soportan manifest.
- No hay `.env.local` (verificado). Esto significa que el entorno por defecto usa `NEXT_PUBLIC_API_URL=http://localhost:8000` del `.env.example`, lo cual puede ser incorrecto para un dispositivo físico o un emulador sin el override localStorage.
- Cobertura de tests en `vitest.config.ts`: umbral de 30% líneas y 30% funciones es muy bajo; indica que se acepta una baja cobertura. Además, `src/app/services/api/client.ts` está explícitamente excluido de la cobertura, a pesar de ser uno de los archivos más críticos.
- `frontend/src/app/components/ui/data-states.tsx`: no hay manejo de errores de red específicos para cada tipo de contenido (ej. si `opportunities` falla pero `history` funciona, el componente `DataState` muestra un error genérico, sin contexto de qué sección falló).
- `frontend/src/app/pages/auth/login/page.tsx` y `register/page.tsx`: no hay validación de fuerza de contraseña (solo mínimo 8 caracteres), ni verificación de formato de email más allá del regex básico de Zod.
- `frontend/src/app/components/opportunity/AgentResult.tsx`: recibe props estáticas. Si el análisis del agente requiere actualización en tiempo real (ej. cambio en la recomendación), el componente no se re-renderiza automáticamente a menos que el padre le pase nuevas props. No hay mecanismo de actualización en vivo.
- `frontend/src/app/layout/sidebar.tsx`: los items de navegación no usan `aria-current` para indicar la página activa. Un usuario con lector de pantalla no sabe en qué sección está.
- `frontend/src/app/layout/MobileTabBar.tsx`: aunque usa `aria-label` en `nav`, los links individuales no tienen `aria-label` explícito (solo texto visible "Inicio", "Buscar", etc.). Esto es accesible básico, pero podría mejorarse con contexto más claro.

--- QUÉ FALTA ---

- Registro del Service Worker en el frontend (código que llame a `navigator.serviceWorker.register`). No se encuentra en ningún archivo de React auditado.
- Manifest PWA (`public/manifest.json`) con iconos, nombre, tema, start_url, display, etc. Completamente ausente.
- `.env.local` con valores reales para desarrollo (especialmente `NEXT_PUBLIC_API_URL` y `CAPACITOR_ANDROID_SCHEME`). No existe; el build usaría los valores por defecto del `.env.example`.
- Pruebas de integración o E2E para el frontend (solo hay archivos `e2e/*.yaml` que parecen definiciones, no evidencia de ejecución automatizada). No hay scripts de `cypress` o `playwright` en `package.json`.
- Tests de UI para componentes (`tests/` cubre servicios, store y hooks, pero no componentes de página o UI interactiva). `vitest.config.ts` confirma que la cobertura está acotada a `store/**` y `services/**`.
- Mecanismo de invalidación remota para caché de marcas/modelos (`getStaticBrandsAndModels`). Falta endpoint de backend que exponga la versión o timestamp de datos estáticos.
- Manejo de errores específicos en formularios de login/registro (diferenciar 401, 422, 500, red). Falta parseo del error del backend (ej. mensaje de error detallado).
- Componente `OfflineBanner` (`use-offline.tsx`) no fue auditado en detalle; falta verificación de que funcione correctamente con el Service Worker y con la detección de red (`useNetworkStatus`).
- Accesibilidad avanzada: no hay `skip-to-content`, `aria-live` en errores/loading/vacío, `aria-busy` en skeletons, `aria-label` en todos los botones sin texto visible.
- No hay mecanismo de notificación push o actualización en segundo plano para datos críticos (oportunidades, deals) en el frontend (aunque hay `push-notifications.ts`, no se auditó su integración).
- No hay manejo de timeout visual para queries (ej. si una query tarda más de X segundos, no hay mensaje específico de "tardando más de lo esperado").
- No hay validación de datos recibidos del backend (ej. si `Opportunity` llega sin `vehicle`, el componente `OpportunityCard` podría romper con errores de renderizado si no se maneja `null`). Aunque el componente usa `v?.brand`, no hay defensa contra datos corruptos (ej. `year` como string en lugar de número).
- No hay documentación de API del frontend (`docs/` no describe los endpoints consumidos ni los contratos de datos esperados por los componentes).
- No hay script de `pre-build-check` o `lint` configurado para validar accesibilidad (ej. `axe-core` o `eslint-plugin-jsx-a11y`).
- `frontend/src/app/config/firebase.ts` y `google-clients.ts`: no auditados en detalle; falta verificación de que los valores de Firebase se carguen correctamente y que haya manejo de errores si faltan (`google-auth.ts` lanza error claro según `.env.example`, pero no se verificó en código).
- `frontend/src/app/services/offline-queue.ts`: no auditado en detalle; falta verificación de que las mutaciones offline se sincronicen correctamente y que haya manejo de errores de red durante la sincronización.
- No hay componente de "Estado vacío" con imagen o ilustración (solo texto e icono); podría mejorar la UX visual.
- No hay componente de "Estado de error de red" específico para cada sección (solo `ErrorDisplay` genérico y el banner del dashboard para backend down).
- `frontend/src/app/layout/AppShell.tsx`: en móvil, el contenido (`main`) tiene `pt-3` y `pb-24`, pero no hay manejo de teclado virtual (ej. si se abre un input, la barra inferior podría ocultar el contenido). No hay ajuste dinámico para el teclado.
- No hay componente de "Modal" o "Drawer" de error para mostrar detalles del error (ej. código de estado, mensaje del servidor) al usuario técnico o administrador.
- No hay verificación de que `NEXT_PUBLIC_FIREBASE_API_KEY` esté definida antes de inicializar Firebase (`firebase.ts` no leído completo, pero `.env.example` indica que si está vacío, `auth=null` y se lanza un error claro; falta verificación en código).
- No hay verificación de que `capacitor.config.ts` esté sincronizado con `android/app/src/main/AndroidManifest.xml` y `build.gradle` para la versión del esquema (`http` vs `https`).

--- EVIDENCIA DE ARCHIVOS ESPECÍFICOS ---

- `frontend/src/app/services/api/client.ts:178` (cliente axios completo con retry y refresh)
- `frontend/src/app/services/search.ts:84-103` (getStaticBrandsAndModels con caché local estático)
- `frontend/src/app/services/opportunities.ts:44-57` (fetchOpportunities real)
- `frontend/src/app/services/deals.ts:54-66` (fetchDeals real)
- `frontend/src/app/services/health.ts:18-30` (fetchHealth con manejo de 503)
- `frontend/src/app/components/ui/data-states.tsx:1-177` (loading, error, empty, skeleton, wrapper)
- `frontend/src/app/components/ui/ErrorDisplay.tsx:1-71` (clasificación de errores sin aria-live)
- `frontend/src/app/components/ui/EmptyState.tsx:1-55` (estado vacío sin aria-live)
- `frontend/src/app/components/ui/btn.ts:1-41` (botón sin aria-label por defecto)
- `frontend/src/app/components/ui/input.tsx:1-40` (input con label accesible básico)
- `frontend/src/app/components/auth/auth-guard.tsx:1-53` (protección de rutas)
- `frontend/src/app/layout/app-shell.tsx:60-82` (layout móvil/desktop)
- `frontend/src/app/layout/navbar.tsx:1-67` (header con botón de notificaciones inaccesible en línea 34)
- `frontend/src/app/layout/sidebar.tsx:1-61` (navegación sin aria-current)
- `frontend/src/app/layout/MobileTabBar.tsx:1-74` (navegación inferior accesible básico)
- `frontend/src/app/features/auth/login-page.tsx:1-163` (formulario login con zod)
- `frontend/src/app/features/auth/register-page.tsx:1-180` (formulario registro con zod)
- `frontend/src/app/features/search/SearchFilters.tsx:1-317` (formulario de búsqueda accesible)
- `frontend/src/app/dashboard/page.tsx:1-299` (página real con datos del backend)
- `frontend/src/app/store/auth-store.ts:1-117` (store de autenticación con JWT exp check)
- `frontend/src/app/hooks/useNetworkStatus.ts:1-55` (estado de red)
- `frontend/src/app/hooks/useApiError.ts:1-72` (manejo de errores con toast)
- `frontend/src/app/config/api-url.ts:1-60` (resolución jerárquica de URL)
- `frontend/src/app/services/api/storage-cache.ts:1-101` (caché localStorage)
- `frontend/src/app/components/opportunities/OpportunityCard.tsx:1-82` (card con imagen alt)
- `frontend/src/app/components/opportunity/AgentResult.tsx:1-45` (presentacional)
- `frontend/src/app/components/home/HomeGreeting.tsx`, `KpiRow.tsx`, `OpportunityTeaserCard.tsx`, `RecentItemCard.tsx`: presentacionales.
- `frontend/src/app/features/home/HomeGreeting.tsx`, `KpiRow.tsx`: componentes presentacionales para dashboard.
- `frontend/public/service-worker.js:1-147` (SW existente, sin registro en React)
- `frontend/next.config.ts:1-59` (configuración de build, headers de seguridad)
- `frontend/package.json`: no leído completamente, pero se confirma la existencia de scripts.
- `frontend/.env.local`: NO EXISTE.
- `frontend/public/manifest.json`: NO EXISTE.
- `frontend/src/__tests__/services/api/client.test.ts`: test de retry con mock de axios.
- `frontend/src/__tests__/store/auth-store.test.ts`: test de persistencia y expiración.
- `frontend/src/__tests__/components/auth-guard.test.tsx`: test de protección.
- `frontend/src/__tests__/hooks/use-cached-query.test.tsx`: test de caché.
- `frontend/src/__tests__/services/search.test.ts`, `deals.test.ts`, `opportunities.test.ts`: tests con mock de api.
- `frontend/src/__tests__/setup.ts`: solo jest-dom.
- `frontend/src/app/providers.tsx`: React Query provider con retry limitado, ToastProvider, OfflineBanner.
- `frontend/src/app/layout.tsx`: RootLayout con lang="es", Providers, OfflineBanner.
- `docs/MOBILE_PRODUCT_CONTEXT.md`: contexto de diseño móvil.
- `docs/TODO.MOBILE_HOME1.md`: checklist de tareas completadas.
- `docs/BUILD.md`: guía de build con Capacitor.

--- CONCLUSIÓN ---

El frontend web (`frontend/`) está estructurado como una aplicación Next.js con export estático (`output: "export"`), diseñada para ser consumida tanto en navegador como en Capacitor (móvil). Tiene una arquitectura clara: servicios que consumen una API real (`api/client`), hooks para estado y red, componentes UI reutilizables, páginas con estados de carga/error/vacío, y protección de rutas (`AuthGuard`). La conexión con el backend es real (no simulada) para la mayoría de los servicios, aunque los datos estáticos de marcas/modelos (`getStaticBrandsAndModels`) y los datos de presentación (`AgentResult`, `HomeGreeting`) son locales o reciben props del padre. Los tests cubren servicios y lógica crítica (store, api retry, hooks de caché, auth) pero no cubren la UI interactiva ni los componentes de página. Hay fallas de accesibilidad (botones sin `aria-label`, falta de `aria-live` para estados dinámicos), ausencia de PWA (`manifest.json` no existe, SW no registrado), ausencia de `.env.local`, manejo de errores genérico en formularios (no distingue red de credenciales), y baja cobertura de tests para componentes de UI. El Service Worker existe en archivos pero no hay evidencia de registro en el código, por lo que es posible que no funcione en producción. No hay mecanismos de validación de esquema de datos recibidos del backend ni de actualización remota para caché estática. El código está bien organizado y sigue convenciones de Next.js y React, con uso de `lucide-react`, `react-hook-form`, `zod`, `zustand`, `tanstack/react-query`, y `capacitor`. Se recomienda mejorar accesibilidad (agregar `aria-label` a botones sin texto, `aria-live` para errores/loading/vacío, `aria-busy` para skeletons, `aria-current` en navegación), registrar el Service Worker (`navigator.serviceWorker.register`), agregar `manifest.json` para PWA, crear `.env.local` con valores reales de desarrollo, ampliar la cobertura de tests a componentes (especialmente UI interactiva y formularios), y mejorar el manejo de errores en formularios de autenticación para distinguir errores de red, credenciales y servidor.
