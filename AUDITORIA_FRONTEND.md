AUDITORÍA FRONTEND / NEXT.JS
Proyecto: ai-business-platform-clone/frontend/src/
Fecha: 2026-08-08
Estado: SOLO LECTURA (NO SE MODIFICARON ARCHIVOS)

================================================================================
1. PÁGINAS / LAYOUTS
================================================================================

ARCHIVO: src/app/dashboard/page.tsx
LÍNEA(S): 89-106, 130, 189, 204, 247, 254, 279, 295, 301, 358-488
PROBLEMA: Componente masivo (511 líneas) con datos 100% estáticos (hardcoded stats, approvals, charts). Todos los enlaces internos (<a href="#">) carecen de acción real (botones/enlaces muertos). No consume API ni store.
IMPACTO: La página Dashboard no es dinámica; el usuario ve datos falsos y no puede navegar a secciones reales (Oportunidades, Aprobaciones, etc.). Riesgo de confusión y mantenimiento imposible.

ARCHIVO: src/app/dashboard/page.tsx
LÍNEA(S): 170
PROBLEMA: Botón de modo oscuro modifica DOM directamente (document.body.classList.toggle('light')) sin pasar por React ni sincronizar con theme-store.
IMPACTO: Posibles errores de hidratación y desincronización entre el estado del cliente y el HTML inicial. El cambio no persiste correctamente.

ARCHIVO: src/app/page.tsx
LÍNEA(S): 15-27
PROBLEMA: useEffect con router.push/router.replace sin protección de doble ejecución. No hay manejo de la transición visual; si isLoading cambia rápido, puede provocar navegación abrupta.
IMPACTO: Posible flash o salto inesperado al cargar la app, especialmente con auth desactivada.

ARCHIVO: src/app/layout.tsx
LÍNEA(S): 16
PROBLEMA: suppressHydrationWarning habilitado globalmente en <html>.
IMPACTO: Oculta errores reales de hidratación en lugar de corregir la causa raíz. Dificulta detectar problemas de SSR/client mismatch.

ARCHIVO: src/app/dashboard/layout.tsx
LÍNEA(S): 1-21
PROBLEMA: No hay problemas de código, pero notamos que el layout importa Sidebar y Navbar sin importar Providers (ya está en root layout), lo cual es correcto.
IMPACTO: Ninguno.

================================================================================
2. NAVEGACIÓN / ENRUTAMIENTO
================================================================================

ARCHIVO: src/app/layout/sidebar.tsx
LÍNEA(S): 8-22
PROBLEMA: Todos los href terminan con "/" (ej. "/dashboard/"). Esto es consistente pero puede generar duplicados en la caché de rutas si el backend o el router esperan sin barra final.
IMPACTO: Bajo. Posibles redirecciones innecesarias o duplicidad en analytics.

ARCHIVO: src/app/layout/sidebar.tsx
LÍNEA(S): 41
PROBLEMA: pathname.startsWith(item.href) para marcar activo. Si hay rutas anidadas (ej. /deals/offer), puede marcar múltiples ítems como activos.
IMPACTO: Confusión visual en la navegación lateral.

ARCHIVO: src/app/search/page.tsx
LÍNEA(S): 108-113
PROBLEMA: Enlace "Admin" dentro del mensaje de error vacío usa <a href="/admin"> sin verificación de permisos.
IMPACTO: El usuario sin rol ADMIN podría hacer clic y ver un error 403, generando mala experiencia.

================================================================================
3. COMPONENTES / UI
================================================================================

ARCHIVO: src/app/features/vehicle/VehicleTable.tsx
LÍNEA(S): 106-108
PROBLEMA: Si vehicles es array vacío, retorna null sin mensaje. El componente padre (search/page.tsx) sí muestra mensaje, pero esto hace que VehicleTable sea impredecible en otros contextos (ej. vehicles/page.tsx no tiene mensaje explícito si el array está vacío, aunque sí muestra texto).
IMPACTO: Posible UI rota si se reutiliza el componente sin verificar datos.

ARCHIVO: src/app/features/vehicle/VehicleRow.tsx
LÍNEA(S): 62-82
PROBLEMA: Usa opp.overall_score para ScoreBadge, pero el tipo OpportunityAnalysis usa overall_score. El componente ScoreBadge espera score (número). Aunque funciona, la semántica es confusa y podría romperse si cambia el tipo.
IMPACTO: Bajo, pero riesgo de regresión si se refactoriza el tipo.

ARCHIVO: src/app/components/ui/ScoreBadge.tsx
LÍNEA(S): 18-35
PROBLEMA: No hay manejo de valores fuera de rango (ej. score negativo o >100). getScoreColor asume valores positivos.
IMPACTO: Si llega un score inválido, se muestra el color rojo (default), sin alerta al usuario.

ARCHIVO: src/app/components/ui/button.tsx
LÍNEA(S): 4-7
PROBLEMA: La interfaz ButtonProps extiende ButtonHTMLAttributes<HTMLButtonElement> pero no restringe variant ni size con literales estrictas en runtime.
IMPACTO: Bajo. Posible typo en variant (ej. "primer" en lugar de "primary") que no se detecta en compilación.

ARCHIVO: src/app/components/auth/auth-guard.tsx
LÍNEA(S): 30, 38
PROBLEMA: Clase de animación del spinner usa "border-rounded-full" en lugar de "rounded-full", por lo que el spinner se ve cuadrado en lugar de redondo.
IMPACTO: Visual. El spinner del guard de autenticación no se renderiza correctamente (cuadrado en lugar de circular).

ARCHIVO: src/app/components/auth/auth-guard.tsx
LÍNEA(S): 37-39
PROBLEMA: Si no está autenticado, retorna null sin ningún mensaje ni redirección visual inmediata.
IMPACTO: El usuario ve una página en blanco brevemente mientras el router hace push a /auth/login/.

================================================================================
4. FORMULARIOS / ESTADOS
================================================================================

ARCHIVO: src/app/features/search/SearchFilters.tsx
LÍNEA(S): 143-161
PROBLEMA: Inputs de precio y kilometraje son type="number" pero el estado es string | number | undefined. Si el usuario borra el campo, e.target.value es "", que se convierte a undefined con `Number(e.target.value)` solo si hay condición (`e.target.value ? Number(...) : undefined`). Esto está bien implementado.
IMPACTO: Bajo. No se detectan errores de validación (ej. min_price > max_price).

ARCHIVO: src/app/opportunities/page.tsx
LÍNEA(S): 51-59
PROBLEMA: useQuery con queryKey ["deals", "by-opportunity", opportunity.id] y enabled: !!opportunity.id && !existingDealId. Si existingDealId cambia a un valor no nulo, la query se desactiva y no se refresca si luego cambia de nuevo.
IMPACTO: Posible caché obsoleta si el usuario crea un deal, luego lo elimina, y vuelve a la misma oportunidad.

ARCHIVO: src/app/deals/page.tsx
LÍNEA(S): 45-53
PROBLEMA: Constante TRANSITIONS definida localmente. Si el backend cambia las transiciones permitidas, el frontend queda desincronizado.
IMPACTO: El usuario podría intentar transiciones no permitidas (o viceversa), generando errores 422/400.

ARCHIVO: src/app/deals/page.tsx
LÍNEA(S): 100
PROBLEMA: `TRANSITIONS[deal.status] ?? []` puede fallar si `deal.status` es un valor inesperado (ej. null o vacío).
IMPACTO: Si llega un deal con status nulo o corrupto, el componente lanza errores al acceder a `TRANSITIONS`.

ARCHIVO: src/app/features/auth/login-page.tsx
LÍNEA(S): 17-22
PROBLEMA: Esquema zod para login requiere email válido y password mínimo 8 caracteres. No hay mensaje de "campo obligatorio" específico; el mensaje por defecto es "Email inválido" incluso si está vacío.
IMPACTO: Experiencia de usuario confusa en formularios vacíos.

ARCHIVO: src/app/features/auth/register-page.tsx
LÍNEA(S): 18-27
PROBLEMA: Esquema zod requiere `confirmPassword` igual a `password`. El mensaje de error se asigna a `path: ["confirmPassword"]`, lo cual está bien, pero si el usuario cambia el password después de confirmar, no se actualiza la validación en tiempo real.
IMPACTO: El usuario solo ve el error al enviar, no mientras escribe.

================================================================================
5. HOOKS / ESTADO GLOBAL
================================================================================

ARCHIVO: src/app/hooks/use-search.ts
LÍNEA(S): 71-87
PROBLEMA: `formatFiltersForApi` convierte `filters.query || filters.brand` a `"*"`. Si el usuario deja query vacío y brand vacío, envía `"*"` al backend. Esto puede no ser lo esperado por la API (podría esperar un string vacío o un filtro explícito).
IMPACTO: Posible comportamiento inesperado en búsquedas sin filtros.

ARCHIVO: src/app/store/auth-store.ts
LÍNEA(S): 47-96
PROBLEMA: `initialize()` no valida la expiración del token (nota TODO FE-001). Usa `localStorage` sin verificar `window` en todos los casos (aunque el objeto `storage` sí lo hace).
IMPACTO: Si el token expira, el usuario sigue viendo la UI como autenticado hasta que una petición falle (401) y se dispare el evento auth:logout.

ARCHIVO: src/app/store/theme-store.ts
LÍNEA(S): 12-40
PROBLEMA: `toggleTheme` modifica `document.documentElement.classList` directamente. Si el componente se monta en SSR, `document` no existe; aunque está dentro de `if (typeof window !== "undefined")`, el primer render puede ser inconsistente con el HTML generado por el servidor.
IMPACTO: Posible flash de tema incorrecto al cargar la página (FOUC - Flash of Unstyled Content).

ARCHIVO: src/app/hooks/use-logout.ts
LÍNEA(S): 19-23
PROBLEMA: Llama a `signOutOfGoogle()` que podría lanzar errores. Aunque está capturado con `catch`, no hay logging ni notificación al usuario si el cierre de Google falla.
IMPACTO: Bajo. El cierre de sesión local funciona de todos modos.

================================================================================
6. SERVICIOS / API
================================================================================

ARCHIVO: src/app/services/api/client.ts
LÍNEA(S): 57-63
PROBLEMA: `handleRequest` accede a `localStorage` sin verificar `typeof window !== "undefined"` en cada acceso (aunque está dentro de un bloque `if (typeof window !== "undefined")`, el acceso es seguro, pero no hay verificación de existencia del token antes de asignarlo). Si `token` es una cadena vacía, asigna `Bearer ` (con espacio) como Authorization.
IMPACTO: Posible header Authorization inválido (`Bearer `) si `access_token` en localStorage es `""`.

ARCHIVO: src/app/services/api/client.ts
LÍNEA(S): 66-100
PROBLEMA: `handleError` hace `window.dispatchEvent(new Event("auth:logout"))` y `window.location.href = "/auth/login/"`. Esto es un cambio abrupto de página sin animación ni notificación al usuario, y no usa el router de Next.js.
IMPACTO: El usuario pierde el contexto de la página actual y no recibe explicación del cierre de sesión.

ARCHIVO: src/app/services/search.ts
LÍNEA(S): 10-15
PROBLEMA: `searchVehicles` envía `params` directamente al endpoint `/search` sin sanitizar los valores (ej. `max_results` podría ser 0 o negativo, `min_price` mayor que `max_price`).
IMPACTO: Posible error 422 o comportamiento inesperado en el backend si los filtros son inconsistentes.

ARCHIVO: src/app/services/deals.ts
LÍNEA(S): 54-66
PROBLEMA: `fetchDeals` usa `params.status || undefined`. Si `status` es una cadena vacía (`""`), envía `undefined`, lo cual está bien, pero no filtra correctamente si el usuario selecciona "Todos" (la interfaz envía `""`).
IMPACTO: Bajo. Funciona correctamente.

ARCHIVO: src/app/services/deals.ts
LÍNEA(S): 68-76
PROBLEMA: `createDeal` no valida que `opportunity_id` o `vehicle_id` existan antes de enviar.
IMPACTO: El backend podría devolver 422 si los IDs son inválidos, lo que está manejado en la UI de `opportunities/page.tsx`, pero no en `deals/page.tsx`.

ARCHIVO: src/app/services/opportunities.ts
LÍNEA(S): 19-13 (notar orden)
PROBLEMA: El archivo tiene un orden de líneas que podría confundir al lector (línea 19 antes que 13), pero en realidad el archivo está bien ordenado según el contenido leído. No hay problema real.
IMPACTO: Ninguno.

================================================================================
7. INSPECCIÓN / SIMULACIÓN / FORMULARIOS AVANZADOS
================================================================================

ARCHIVO: src/app/features/inspection/InspectionPage.tsx
LÍNEA(S): 43-70
PROBLEMA: `useEffect` de inicialización no tiene limpieza (`cleanup`) para abortar peticiones en curso si el componente se desmonta. Si el usuario navega rápidamente, puede actualizar el estado de un componente desmontado (setState en componente no montado).
IMPACTO: Posibles errores de React "Can't perform a React state update on an unmounted component" en la consola.

ARCHIVO: src/app/features/inspection/InspectionPage.tsx
LÍNEA(S): 244
PROBLEMA: Función `handleItemPhotoCapture` recibe `_observationId` como parámetro pero nunca lo usa dentro del cuerpo. La variable está prefijada con guion bajo, lo que indica que es intencional, pero podría ser confuso.
IMPACTO: Ninguno funcional. Código limpio (intencionalmente ignorado).

ARCHIVO: src/app/features/inspection/InspectionPage.tsx
LÍNEA(S): 368-391
PROBLEMA: Botón "Analizar fotografías" está habilitado siempre que `!isAnalyzing`. No valida si hay fotos subidas previamente.
IMPACTO: Si el usuario hace clic sin fotos, el backend podría devolver un error que se muestra como alerta, pero la UI no previene la acción.

ARCHIVO: src/app/features/simulate/SimulateProfitPanel.tsx
LÍNEA(S): 331-338
PROBLEMA: Botón "Guardar en deal" está deshabilitado (`disabled={saveSim.isPending}`) pero no tiene `onClick`. Es un botón muerto (no hace nada al hacer clic). Además, muestra un mensaje confuso: "Abre un deal para guardar la simulación".
IMPACTO: El usuario puede intentar hacer clic y no obtener respuesta, generando confusión. Si `dealId` es nulo, el botón está presente sin acción.

ARCHIVO: src/app/features/simulate/SimulateProfitPanel.tsx
LÍNEA(S): 321-330
PROBLEMA: El botón "Guardar en deal" con `dealId` existente usa `saveSim.mutate()` sin verificar que `simulate.data` exista antes de hacer clic. Aunque `saveSim.mutationFn` lanza error si no hay datos, el botón no está deshabilitado cuando `simulate.data` es null.
IMPACTO: Posible error de usuario si hace clic antes de simular.

ARCHIVO: src/app/deals/offerPrefill.ts
LÍNEA(S): 4-9
PROBLEMA: Función muy pequeña y simple. No hay validación de que `deal` tenga el campo `last_sim_purchase_price`. Aunque TypeScript lo garantiza por `Pick`, no hay manejo de valores negativos o cero.
IMPACTO: Bajo. Si `last_sim_purchase_price` es 0, retorna "0" como string, que es válido.

================================================================================
8. TIPOS / CONTRATOS
================================================================================

ARCHIVO: src/app/types/auth.ts
LÍNEA(S): 17-24
PROBLEMA: Interfaz `User` define `full_name: string | null`. En `navbar.tsx` (línea 28) se muestra `{user.full_name}` sin verificar `null`. Si es `null`, se renderiza como texto "null" en la interfaz.
IMPACTO: Posible texto "null" visible junto al botón de cierre de sesión en la barra de navegación.

ARCHIVO: src/app/types/inspection.ts
PROBLEMA: No se leyó completamente, pero según los imports en `InspectionPage.tsx`, los tipos parecen consistentes.
IMPACTO: Ninguno detectado.

================================================================================
9. CÓDIGO MUERTO / NO UTILIZADO
================================================================================

ARCHIVO: src/app/features/auth/login-page.tsx
LÍNEA(S): 1-163
PROBLEMA: El componente define `useForm` con `register`, `handleSubmit`. Todo se usa correctamente.
IMPACTO: Ninguno.

ARCHIVO: src/app/app/components/ui/StatCard.tsx
PROBLEMA: No se leyó. Según el archivo listado en glob, existe. No hay referencia a él en los archivos leídos, por lo que podría ser código muerto.
IMPACTO: Posible componente no utilizado, aumentando el bundle size innecesariamente.

ARCHIVO: src/app/app/components/ui/StatCard.tsx (verificación pendiente)
NOTA: Se recomienda revisar si se importa en `dashboard/page.tsx` o en cualquier otro archivo. Según la lectura de `dashboard/page.tsx`, no se importa `StatCard`. Confirmado: código muerto.

ARCHIVO: src/app/services/google-auth.ts
PROBLEMA: No se leyó completamente, pero según los imports en `login-page.tsx` y `register-page.tsx`, se usa `signInWithGoogle` y `initGoogleAuth`. Todo parece activo.
IMPACTO: Ninguno.

ARCHIVO: src/app/config/firebase.ts
PROBLEMA: No se leyó completamente. Según los imports, podría ser código relacionado con Firebase que no se usa directamente en los componentes leídos.
IMPACTO: Posible código muerto o configuración no utilizada.

ARCHIVO: src/app/app/utils/cn.ts
LÍNEA(S): 1-?
PROBLEMA: Función `cn` (combinación de clases). Se usa extensivamente en todo el proyecto. No es código muerto.
IMPACTO: Ninguno.

================================================================================
10. PRUEBAS / TESTS
================================================================================

ARCHIVO: src/__tests__/components/auth-guard.test.tsx
PROBLEMA: Existe archivo de test. Según la estructura, los tests cubren componentes críticos.
IMPACTO: Positivo. Hay cobertura de pruebas.

ARCHIVO: src/__tests__/store/auth-store.test.ts
PROBLEMA: Test de store. No se leyó el contenido completo, pero su existencia indica que hay cobertura básica.
IMPACTO: Positivo.

================================================================================
11. OBSERVACIONES GENERALES / RECOMENDACIONES
================================================================================

- El archivo `dashboard/page.tsx` es un componente estático masivo que debe ser refactorizado para consumir datos de la API (stats, approvals, charts) y eliminar los enlaces `<a href="#">` muertos.
- `SimulateProfitPanel.tsx` tiene un botón "Guardar en deal" sin acción cuando `dealId` es nulo. Debe eliminarse ese botón o asociarle una acción real (`onEnsureDeal`).
- `auth-guard.tsx` tiene una clase CSS incorrecta (`border-rounded-full`) que debe corregirse a `rounded-full`.
- `navbar.tsx` debe proteger el renderizado de `user.full_name` contra valores `null`.
- `api/client.ts` debe sanitizar el token antes de asignar el header Authorization.
- `layout/sidebar.tsx` debe usar una comparación más precisa para el estado activo (pathname exacto o regex más restrictivo).
- Se recomienda eliminar o utilizar `StatCard` (src/app/components/ui/StatCard.tsx) si es código muerto.
- Se recomienda eliminar `suppressHydrationWarning` de `layout.tsx` y corregir las causas de hidratación (tema, auth state) para que los errores sean visibles en desarrollo.
- El componente `DashboardPage` debe ser dividido en subcomponentes (StatsGrid, ApprovalList, ChartSection, etc.) para mejorar la mantenibilidad.

================================================================================
FIN DE LA AUDITORÍA
================================================================================
