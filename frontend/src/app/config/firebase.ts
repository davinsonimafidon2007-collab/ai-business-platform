import { initializeApp } from "firebase/app";
import {
  getAuth,
  GoogleAuthProvider,
  type Auth,
  type GoogleAuthProvider as GoogleAuthProviderInstance,
} from "firebase/auth";

// MED.007: configuración SOLO vía variables de entorno (NEXT_PUBLIC_FIREBASE_*).
// No hay fallback a valores del proyecto: eso fija el proyecto concreto en el
// bundle y rompe si el repo se reutiliza. Sin NEXT_PUBLIC_FIREBASE_* el login
// Google no está disponible (auth = null) y google-auth.ts lanza un error claro.
const apiKey = process.env.NEXT_PUBLIC_FIREBASE_API_KEY;
const authDomain = process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN;
const projectId = process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID;
const storageBucket = process.env.NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET;
const messagingSenderId = process.env.NEXT_PUBLIC_FIREBASE_SENDER_ID;
const appId = process.env.NEXT_PUBLIC_FIREBASE_APP_ID;

export const firebaseConfigured = Boolean(
  apiKey && authDomain && projectId,
);

let _auth: Auth | null = null;
let _googleProvider: GoogleAuthProviderInstance | null = null;

if (firebaseConfigured) {
  const app = initializeApp({
    apiKey,
    authDomain,
    projectId,
    storageBucket,
    messagingSenderId,
    appId,
  });
  _auth = getAuth(app);
  _googleProvider = new GoogleAuthProvider();
}

export const auth = _auth;
export const googleProvider = _googleProvider;
