# TODO: Producción móvil + despliegue (Capacitor Android)

## Fase 1: Corregir flujo de fotografías (BUG CRÍTICO)
- [ ] **1.1** Backend: Endpoint `POST /{session_id}/photos/upload` multipart (UploadFile)
- [ ] **1.2** Frontend: Agregar captura de foto con cámara en CategoryStep.tsx
- [ ] **1.3** Frontend: Subir foto al backend (inspection.ts service)
- [ ] **1.4** Frontend: Integrar captura/subida en InspectionPage.tsx

## Fase 2: Integrar Capacitor
- [ ] **2.1** Instalar @capacitor/core, @capacitor/cli, @capacitor/camera
- [ ] **2.2** Capacitor init (crear capacitor.config.ts)
- [ ] **2.3** Build Next.js (npm run build)
- [ ] **2.4** Capacitor add android
- [ ] **2.5** Sincronizar (npx cap sync)
- [ ] **2.6** Agregar permisos Android (Camera, Storage)

## Fase 3: Configuración de producción
- [ ] **3.1** Variables de entorno (frontend: .env.production)
- [ ] **3.2** Configurar backend CORS para Android
- [ ] **3.3** Configurar UPLOAD_DIR en backend
- [ ] **3.4** Configurar OpenAI API Key en backend

## Fase 4: Generar APK
- [ ] **4.1** Build Android debug APK (npx cap open android && ./gradlew assembleDebug)
- [ ] **4.2** Verificar APK generada
- [ ] **4.3** Probar instalación y flujo completo

