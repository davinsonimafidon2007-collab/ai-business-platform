# TASK — MOBILE HARDENING / ANDROID PRODUCTION READINESS

Trabaja exclusivamente sobre la versión móvil de ai-business-platform.

OBJETIVO:
Dejar la aplicación Capacitor/Android técnicamente preparada para producción,
Google Play y uso real.

NO des por completada una tarea hasta comprobarla con tests/build cuando el
entorno lo permita.

## 1. Android SDK / Gradle

Actualizar el proyecto para soportar Android 16 / API 36.

Revisar y actualizar coordinadamente:

- frontend/android/variables.gradle
- frontend/android/build.gradle
- frontend/android/gradle/wrapper/gradle-wrapper.properties

Usar una versión de AGP compatible con API 36 y una versión de Gradle
compatible con ella.

No actualizar Capacitor major automáticamente sin analizar compatibilidad.

Después ejecutar:

```
cd frontend
npm ci
npx cap sync android
cd android
./gradlew assembleDebug
```

Si falla, resolver los errores de compatibilidad.

## 2. Release signing

Revisar frontend/android/app/build.gradle y
.github/workflows/mobile-release-cicd.yml.

Unificar el mecanismo de firma.

El workflow debe poder generar:

```
./gradlew bundleRelease
```

usando exclusivamente secretos de GitHub Actions.

No almacenar:

- keystore
- passwords
- alias
- credentials

en Git.

Validar que los argumentos usados por CI realmente son consumidos por
signingConfigs.release.

## 3. Firebase distribution

Corregir mobile-release-cicd.yml.

Añadir workflow_dispatch a:

```yaml
on:
```

para que firebase-dist pueda ejecutarse manualmente.

Verificar también que los artefactos generados existen antes de intentar
distribuirlos.

## 4. Deep links

Revisar:

frontend/src/app/hooks/use-deep-links.ts

Implementar correctamente:

- cold start
- appUrlOpen
- custom scheme
- Android App Links
- navegación desde push notification
- limpieza de listeners

Corregir especialmente la inconsistencia:

deepLinkBuilder.search() vs resolveDeepLinkRoute()

Actualmente el builder coloca la búsqueda en el path mientras el resolver
espera queryParams.

Añadir tests para:

- aibusiness://vehicle/123
- aibusiness://deal/123
- aibusiness://opportunity/123
- aibusiness://search/Toyota
- https://aibusiness.app/vehicle/123
- https://app.aibusiness.com/deal/123
- URL inválida
- cold start

## 5. Push notifications

Revisar:

frontend/src/app/services/push-notifications.ts

Eliminar logs de FCM tokens en producción.

Garantizar:

- registration
- registrationError
- foreground notification
- notification tap
- deep-link navigation
- unregister al cerrar sesión

No mostrar tokens sensibles en logs.

Validar IDs de LocalNotifications para que siempre sean enteros válidos.

Evitar listeners duplicados si initPushNotifications() se ejecuta más de una vez.

Añadir tests.

## 6. FileProvider

Revisar:

frontend/android/app/src/main/res/xml/file_paths.xml

Eliminar:

```xml
external-path path="."
```

Usar únicamente rutas pertenecientes a la aplicación salvo que exista una
necesidad funcional demostrada.

Comprobar que compartir imágenes/archivos sigue funcionando.

## 7. Production network security

Revisar:

- frontend/capacitor.config.ts
- frontend/android/app/src/main/res/xml/network_security_config.xml
- frontend/android/app/src/debug/res/xml/network_security_config.xml

Objetivo:

DEBUG:
- permitir HTTP local cuando sea necesario.

RELEASE:
- HTTPS obligatorio.
- no permitir cleartext arbitrario.

Verificar que la configuración de producción no hereda accidentalmente permisos
de desarrollo.

## 8. App versioning

Crear una única fuente de verdad para la versión móvil.

Debe existir relación:

```
VERSION
  ↓
Android versionName
Android versionCode
NEXT_PUBLIC_APP_VERSION
backend /mobile/version
```

El versionCode debe ser entero y monotónico.

El versionName debe seguir SemVer.

Preparar CI para obtener la versión desde el tag vX.Y.Z cuando sea posible.

## 9. App Links

Verificar:

- AndroidManifest.xml
- assetlinks.json
- capacitor.config.ts

Los hosts definidos actualmente son:

- aibusiness.app
- app.aibusiness.com
- aibusiness.platform

Comprobar que todos tienen sentido y que no existen dominios ficticios
configurados como si fueran producción.

Si alguno no existe realmente, no presentarlo como App Link productivo.

## 10. Android permissions

Auditar AndroidManifest.xml.

Eliminar permisos que no sean utilizados.

Justificar:

- CAMERA
- READ_MEDIA_IMAGES
- READ_EXTERNAL_STORAGE
- WRITE_EXTERNAL_STORAGE
- POST_NOTIFICATIONS
- RECEIVE_BOOT_COMPLETED
- VIBRATE
- USE_BIOMETRIC
- USE_FINGERPRINT

Especialmente revisar permisos obsoletos o redundantes para versiones modernas
de Android.

## 11. CI mobile quality gate

El pipeline móvil debe comprobar como mínimo:

```
npm ci
npm run test:run
npm run check:cap-config
npm run export
npx cap sync android
./gradlew assembleDebug
```

Y en release:

```
./gradlew bundleRelease
```

No declarar móvil "production ready" si el build Android no pasa.

## 12. Tests

Añadir/corregir tests para:

- deep links
- push notification routing
- secure storage
- offline storage
- app version comparison
- app update status
- mobile configuration
- notification permissions
- malformed notification payloads

Ejecutar:

```
npm run test:run
npm run test:coverage
```

## 13. Documentación

Actualizar la documentación móvil con:

- requisitos Android Studio
- JDK
- Android SDK
- variables de entorno
- debug build
- release build
- Firebase
- Google Login
- Push Notifications
- Deep Links
- App Links
- signing
- GitHub Actions
- publicación en Google Play

## REGLA FINAL

No afirmar que Android está terminado simplemente porque TypeScript compila.

El objetivo es:

- WEB → OK
- CAPACITOR → OK
- ANDROID BUILD → OK
- DEBUG APK → OK
- RELEASE AAB → OK
- PUSH → OK
- DEEP LINKS → OK
- GOOGLE LOGIN → OK
- VERSIONING → OK
- CI/CD → OK
- SECURITY → OK

Cuando termines:

1. Ejecuta todos los tests posibles.
2. Ejecuta el build Android.
3. Ejecuta el release build si existen las credenciales.
4. Enumera exactamente qué pasó y qué no pudo probarse.
5. No ocultes ningún fallo.
6. Devuelve una tabla:
   - Área
   - Estado
   - Evidencia
   - Pendiente
7. Solo marca 100% cuando realmente esté validado.
