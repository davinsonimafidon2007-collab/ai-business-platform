import { initializeApp } from "firebase/app";
import { getAuth, GoogleAuthProvider } from "firebase/auth";

// Configuración vía variables de entorno (NEXT_PUBLIC_*) con fallback a los
// valores del proyecto para que funcione sin tocar código.
const firebaseConfig = {
  apiKey:
    process.env.NEXT_PUBLIC_FIREBASE_API_KEY ||
    "AIzaSyDKQU1xQlH_v6Y79-69phr2jsQ4QWuWe_o",
  authDomain:
    process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN ||
    "ai-business-platform-e7043.firebaseapp.com",
  projectId:
    process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID ||
    "ai-business-platform-e7043",
  storageBucket:
    process.env.NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET ||
    "ai-business-platform-e7043.firebasestorage.app",
  messagingSenderId:
    process.env.NEXT_PUBLIC_FIREBASE_SENDER_ID || "983773208764",
  // Completar desde Firebase Console > Project Settings > Web App cuando se
  // conozcan. No son obligatorios para el login, pero evitan warnings de
  // inicialización en el SDK.
  appId: process.env.NEXT_PUBLIC_FIREBASE_APP_ID || undefined,
  measurementId: process.env.NEXT_PUBLIC_FIREBASE_MEASUREMENT_ID || undefined,
};

const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);
export const googleProvider = new GoogleAuthProvider();
