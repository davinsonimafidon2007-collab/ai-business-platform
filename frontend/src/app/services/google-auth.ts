"use client";

import { Capacitor } from "@capacitor/core";
import { signInWithPopup, signOut } from "firebase/auth";
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

export async function signInWithGoogle(): Promise<void> {
  let idToken: string | null = null;
  const platform = Capacitor.getPlatform();

  if (platform !== "web") {
    // Android / iOS – use the native Capacitor Google Auth plugin
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const { GoogleAuth } = require("@codetrix-studio/capacitor-google-auth");
    const response = await GoogleAuth.signIn({
      clientId: ANDROID_CLIENT_ID,
      androidClientId: ANDROID_CLIENT_ID,
      iosClientId: WEB_CLIENT_ID,
    });
    idToken = response.authentication?.idToken ?? null;
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
  localStorage.setItem("user", JSON.stringify(userRes.data));
  useAuthStore.getState().setUser(userRes.data);
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
