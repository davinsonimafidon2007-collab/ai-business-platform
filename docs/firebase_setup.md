# 📋 Guía de Configuración de Firebase y Google Login

Esta guía detalla paso a paso cómo configurar **Firebase** y **Google Sign-In** en la plataforma, tanto para el backend (FastAPI) como para el frontend (Next.js / Capacitor).

---

## 🚀 Paso 1: Crear un proyecto en Firebase

1. Ve a la consola de [Firebase Console](https://console.firebase.google.com/).
2. Haz clic en **Agregar proyecto** (o selecciona uno existente).
3. Introduce el nombre del proyecto (ej: `ai-business-platform`).
4. Selecciona si quieres habilitar Google Analytics (opcional) y haz clic en **Crear proyecto**.

---

## 🔐 Paso 2: Habilitar la Autenticación de Google

1. En el menú lateral izquierdo de tu proyecto de Firebase, ve a **Build** > **Authentication**.
2. Haz clic en **Comenzar** (Get Started).
3. En la pestaña **Método de inicio de sesión** (Sign-in method), haz clic en **Agregar nuevo proveedor**.
4. Selecciona **Google** de la lista.
5. Habilita el interruptor de Google, configura el nombre público del proyecto y selecciona un correo de soporte.
6. Haz clic en **Guardar**.

---

## 💻 Paso 3: Configuración del Frontend (Web App)

Para que el frontend interactúe con Firebase Auth, debes registrar una aplicación web y configurar las claves públicas.

### 3.1 Registrar la Web App en Firebase
1. En la página de descripción general de tu proyecto de Firebase, haz clic en el icono de **Web (`</>`)** para agregar una aplicación.
2. Introduce un apodo para la aplicación (ej: `ABP Web`) y haz clic en **Registrar app**.
3. Te mostrará un objeto de configuración similar a este:
   ```javascript
   const firebaseConfig = {
     apiKey: "TU_API_KEY",
     authDomain: "TU_PROJECT_ID.firebaseapp.com",
     projectId: "TU_PROJECT_ID",
     storageBucket: "TU_PROJECT_ID.appspot.com",
     messagingSenderId: "TU_MESSAGING_SENDER_ID",
     appId: "TU_APP_ID"
   };
   ```

### 3.2 Configurar las Variables en el Frontend
En tu archivo de entorno de frontend (ej: `frontend/.env.local`), actualiza los valores públicos obtenidos en el paso anterior:
```env
NEXT_PUBLIC_FIREBASE_API_KEY=TU_API_KEY
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=TU_PROJECT_ID.firebaseapp.com
NEXT_PUBLIC_FIREBASE_PROJECT_ID=TU_PROJECT_ID
NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET=TU_PROJECT_ID.appspot.com
NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID=TU_MESSAGING_SENDER_ID
NEXT_PUBLIC_FIREBASE_APP_ID=TU_APP_ID
```

---

## 🛠️ Paso 4: Configuración del Backend (Firebase Admin SDK)

El backend de FastAPI utiliza la biblioteca `firebase-admin` para verificar de forma segura los tokens de identidad (`id_token`) enviados por el frontend. Para esto, requiere una **Service Account** (Cuenta de Servicio).

### 4.1 Generar la Clave de la Cuenta de Servicio
1. En la consola de Firebase, haz clic en el icono de engranaje **⚙️** al lado de "Descripción general del proyecto" y selecciona **Configuración del proyecto** (Project settings).
2. Ve a la pestaña **Cuentas de servicio** (Service accounts).
3. Haz clic en el botón **Generar nueva clave privada** (Generate new private key).
4. Confirma haciendo clic en **Generar clave**. Se descargará automáticamente un archivo `.json` que contiene las credenciales altamente confidenciales.

⚠️ **ADVERTENCIA DE SEGURIDAD:** Este archivo `.json` contiene claves criptográficas privadas que permiten el acceso total a tu proyecto de Firebase. **NUNCA** lo subas al repositorio de git.

### 4.2 Configurar el Backend con las Credenciales
Tienes dos opciones para pasar estas credenciales al backend (configuradas en tu archivo `.env` en la raíz):

#### Opción A: Guardar el JSON directamente en una variable (Recomendada para Docker/Producción)
Copia todo el contenido del archivo `.json` descargado y pégalo como una sola línea en la variable `FIREBASE_CREDENTIALS_JSON`:
```env
FIREBASE_CREDENTIALS_JSON='{"type": "service_account", "project_id": "TU_PROJECT_ID", ...}'
```

#### Opción B: Especificar la ruta al archivo local
Guarda el archivo en un directorio local seguro (fuera de la carpeta git o agregándolo a `.gitignore`) y configura su ruta en `FIREBASE_CREDENTIALS_PATH`:
```env
FIREBASE_CREDENTIALS_PATH=/ruta/a/tu/archivo-credenciales.json
```

---

## ⚙️ Paso 5: Comportamiento por Entornos (`FIREBASE_REQUIRED`)

El backend maneja de forma inteligente la presencia de las credenciales de Firebase dependiendo del entorno y de las variables configuradas:

1. **Desarrollo/Test (`ENVIRONMENT=development` o `ENVIRONMENT=test`):**
   - Firebase es **opcional**. Si las credenciales no están presentes, la aplicación arrancará normalmente pero registrará un `WARNING` en los logs y los endpoints de Google Login devolverán un error claro `401 Unauthorized` al intentar usarse.

2. **Producción (`ENVIRONMENT=production`):**
   - El comportamiento depende de la variable `FIREBASE_REQUIRED` en el archivo `.env`:
     - `FIREBASE_REQUIRED=false` (por defecto): Se comporta igual que en desarrollo (con warnings en el arranque).
     - `FIREBASE_REQUIRED=true`: La aplicación **no arrancará** si faltan las credenciales de Firebase, aplicando un principio de fail-fast para garantizar que los despliegues de producción no inicien con el login de Google caído.
