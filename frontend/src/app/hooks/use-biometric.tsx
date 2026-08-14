"use client";

/**
 * MOB-P2-004: Biometric Authentication Service
 *
 * Dependencia: @capgo/capacitor-native-biometric
 */

import { useState, useEffect, useCallback } from "react";
import { Capacitor } from "@capacitor/core";

export interface BiometricState {
  isAvailable: boolean;
  biometryType: string;
  isEnrolled: boolean;
  isLoading: boolean;
  error: string | null;
}

const INITIAL_STATE: BiometricState = {
  isAvailable: false,
  biometryType: "none",
  isEnrolled: false,
  isLoading: true,
  error: null,
};

export function useBiometricAuth() {
  const [state, setState] = useState<BiometricState>(INITIAL_STATE);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  const checkAvailability = useCallback(async () => {
    if (!Capacitor.isNativePlatform()) {
      setState({
        isAvailable: false,
        biometryType: "none",
        isEnrolled: false,
        isLoading: false,
        error: "Solo disponible en nativo",
      });
      return;
    }
    try {
      const { NativeBiometric } = await import("@capgo/capacitor-native-biometric");
      const result = await NativeBiometric.isAvailable();
      setState({
        isAvailable: result.isAvailable,
        biometryType: String(result.biometryType || "none"),
        isEnrolled: result.isAvailable,
        isLoading: false,
        error: null,
      });
    } catch (err) {
      setState({
        isAvailable: false,
        biometryType: "none",
        isEnrolled: false,
        isLoading: false,
        error: err instanceof Error ? err.message : "Error",
      });
    }
  }, []);

  useEffect(() => {
    // Deferred: el lint react-hooks prohíbe setState síncrono en effects.
    const timer = setTimeout(() => {
      void checkAvailability();
    }, 0);
    return () => clearTimeout(timer);
  }, [checkAvailability]);

  const authenticate = useCallback(async (): Promise<boolean> => {
    if (!Capacitor.isNativePlatform()) return false;
    try {
      const { NativeBiometric } = await import("@capgo/capacitor-native-biometric");
      await NativeBiometric.verifyIdentity({
        reason: "Autenticar para acceder a AI Business Platform",
        title: "Desbloquear app",
        subtitle: "Usa tu huella o Face ID",
        description: "Verifica tu identidad para continuar",
        maxAttempts: 3,
      });
      setIsAuthenticated(true);
      return true;
    } catch {
      setIsAuthenticated(false);
      return false;
    }
  }, []);

  return { state, isAuthenticated, authenticate, refresh: checkAvailability };
}

export function BiometricUnlockButton({
  onSuccess,
  onError,
}: {
  onSuccess?: () => void;
  onError?: (error: string) => void;
}) {
  const { state, authenticate } = useBiometricAuth();
  if (!state.isAvailable || state.isLoading) return null;

  const handlePress = async () => {
    const success = await authenticate();
    if (success) {
      onSuccess?.();
    } else {
      onError?.("Autenticación fallida");
    }
  };

  return (
    <button
      onClick={() => void handlePress()}
      className="flex items-center justify-center gap-2 w-full rounded-lg border border-secondary-300 dark:border-secondary-600 bg-white dark:bg-secondary-800 px-4 py-3 text-sm font-medium text-secondary-700 dark:text-secondary-300 hover:bg-secondary-50 dark:hover:bg-secondary-700 transition-colors"
    >
      <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M12 11c0 3.517-1.009 6.799-2.753 9.571m-3.44-2.04l.054-.09A13.916 13.916 0 008 11a4 4 0 118 0c0 1.017-.07 2.019-.203 3m-2.118 6.844A21.88 21.88 0 0015.171 17m3.839 1.132c.645-2.266.99-4.659.99-7.131A8 8 0 008 4.07M3 15.364c.64-1.319 1-2.8 1-4.364 0-1.457.2-2.85.577-4.147"
        />
      </svg>
      Desbloquear con {state.biometryType === "faceId" ? "Face ID" : "huella dactilar"}
    </button>
  );
}
