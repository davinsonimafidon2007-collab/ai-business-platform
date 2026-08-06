"use client";

import { Capacitor } from "@capacitor/core";
import {
  signInWithPopup,
  signInWithCredential,
  GoogleAuthProvider,
  signOut,
} from "firebase/auth";
import { auth, googleProvider } from "@/app/config/firebase";
import { api } from "@/app/services/api/client";
import { useAuthStore } from "@/app/store/auth-store";
import type { AuthResponse, User } from "@/app/types/auth";

// Web client ID from google-services.json (client_type: 3)
const WEB_CLIENT_ID =
  "983773208764-oevega4uglktmrisjrh41teq5mjb270n.apps.googleusercontent.com";

// Android client ID from google-services.json (client_type: 1)
const ANDROID_CLIENT_ID =
  "983773208764-7i0hfifq4ni324qnugvj0a79bu09fh4t.apps.googleusercontent.com";

// The plugin requires initialize() to be called once before signIn() will
// work on native Android/iOS — without it, signIn() fails silently at the
// native layer and no account picker ever appears. Call this once at app
// startup (see Providers in app/providers.tsx).
export function initGoogleAuth(): void {
  if (Capacitor.getPlatform() === "web") return;
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const { GoogleAuth } = require("@codetrix-studio/capacitor-google-auth");
  GoogleAuth.initialize({
    clientId: WEB_CLIENT_ID,
    scopes: ["profile", "email"],
    grantOfflineAccess: true,
  }).catch((err: unknown) => {
    // eslint-disable-next-line no-console
    console.error("GoogleAuth.initialize() failed:", err);
  });
}

export async function signInWithGoogle(): Promise<void> {
  let idToken: string | null = null;
  const platform = Capacitor.getPlatform();

  if (platform !== "web") {
    // Android / iOS – el plugin nativo devuelve un ID token de Google
    // (emitido por accounts.google.com), NO un ID token de Firebase.
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const { GoogleAuth } = require("@codetrix-studio/capacitor-google-auth");
    const response = await GoogleAuth.signIn({
      clientId: WEB_CLIENT_ID,
      androidClientId: ANDROID_CLIENT_ID,
      iosClientId: WEB_CLIENT_ID,
    });

    const nativeIdToken = response.authentication?.idToken ?? null;
    if (!nativeIdToken) {
      throw new Error("No se recibió el token nativo de Google");
    }

    // Intercambiamos el token nativo de Google por una sesión de Firebase,
    // para que el backend (que verifica tokens de Firebase) pueda validarlo.
    const credential = GoogleAuthProvider.credential(nativeIdToken);
    const firebaseResult = await signInWithCredential(auth, credential);
    idToken = await firebaseResult.user.getIdToken();
  } else {
    // Web – use Firebase Auth popup
    const result = await signInWithPopup(auth, googleProvider);
    idToken = await result.user.getIdToken();
  }

  if (!idToken) {
    throw new Error("No se recibió el token de Google");
  }

  // Send the Firebase ID token to the backend for verification
  const authRes = await api.post<AuthResponse>("/auth/google", {
    id_token: idToken,
  });

  localStorage.setItem("access_token", authRes.data.access_token);
  localStorage.setItem("refresh_token", authRes.data.refresh_token);

  const userRes = await api.get<User>("/auth/me");
  // Persistencia unificada via setSession (mismo contrato que login/register).
  useAuthStore.getState().setSession({
    accessToken: authRes.data.access_token,
    refreshToken: authRes.data.refresh_token,
    user: userRes.data,
  });
}

export async function signOutOfGoogle(): Promise<void> {
  const platform = Capacitor.getPlatform();
  if (platform !== "web") {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const { GoogleAuth } = require("@codetrix-studio/capacitor-google-auth");
    await GoogleAuth.signOut();
  } else {
    await signOut(auth);
  }
}
