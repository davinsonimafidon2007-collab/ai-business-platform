"use client";

/**
 * MOB-P1-003: Onboarding automático de configuración de URL
 * Detecta primer arranque en dispositivo móvil físico y guía al usuario.
 */

import { useState, useEffect, useCallback } from "react";
import { Capacitor } from "@capacitor/core";
import { getApiBaseUrl, setApiBaseUrl } from "@/app/config/api-url";
import { fetchHealth } from "@/app/services/health";
import { X, Wifi, Settings, ArrowRight, CheckCircle, AlertCircle } from "lucide-react";

const ONBOARDING_KEY = "abp_onboarding_completed_v1";
const HAS_SHOWN_ONBOARDING_KEY = "abp_has_shown_onboarding";

interface OnboardingModalProps {
  onComplete: () => void;
  onDismiss: () => void;
}

export function OnboardingModal({ onComplete, onDismiss }: OnboardingModalProps) {
  const [step, setStep] = useState<"detect" | "input" | "test" | "success" | "error">(() => {
    if (typeof window === "undefined") return "detect";
    const baseUrl = getApiBaseUrl();
    const isDefaultLocalhost =
      baseUrl.includes("localhost") || baseUrl.includes("127.0.0.1") || baseUrl.includes("10.0.2.2");
    return isDefaultLocalhost ? "input" : "test";
  });
  const [url, setUrl] = useState<string>(() => {
    if (typeof window === "undefined") return "";
    return getApiBaseUrl();
  });
  const [error, setError] = useState<string | null>(null);
  const [isTesting, setIsTesting] = useState(false);

  const testConnection = useCallback(async (testUrl: string) => {
    setIsTesting(true);
    setError(null);
    try {
      setApiBaseUrl(testUrl);
      const health = await fetchHealth();
      if (health && health.status === "ok") {
        setStep("success");
        if (typeof window !== "undefined") {
          localStorage.setItem(ONBOARDING_KEY, "true");
          localStorage.setItem(HAS_SHOWN_ONBOARDING_KEY, "true");
        }
      } else {
        setStep("error");
        setError("El servidor respondió pero no está saludable.");
      }
    } catch {
      setStep("error");
      setError(
        "No se pudo conectar con el servidor. Verifica que:\n• El backend está ejecutándose\n• La IP y puerto son correctos\n• El firewall permite conexiones"
      );
    } finally {
      setIsTesting(false);
    }
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const baseUrl = getApiBaseUrl();
    const isDefaultLocalhost =
      baseUrl.includes("localhost") || baseUrl.includes("127.0.0.1") || baseUrl.includes("10.0.2.2");
    if (!isDefaultLocalhost) {
      // Deferred: el lint react-hooks prohíbe setState síncrono en effects.
      const timer = setTimeout(() => void testConnection(baseUrl), 0);
      return () => clearTimeout(timer);
    }
    return undefined;
  }, [testConnection]);

  const handleTest = () => {
    const trimmed = url.trim().replace(/\/+$/g, "");
    if (!trimmed) {
      setError("Introduce una URL válida");
      return;
    }
    if (!/^https?:\/\/.+/.test(trimmed)) {
      setError("La URL debe empezar con http:// o https://");
      return;
    }
    void testConnection(trimmed);
  };

  const handleSkip = () => {
    if (typeof window !== "undefined") {
      localStorage.setItem(HAS_SHOWN_ONBOARDING_KEY, "true");
    }
    onDismiss();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="w-full max-w-md rounded-2xl bg-white dark:bg-secondary-900 shadow-2xl overflow-hidden">
        <div className="bg-primary-600 px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2 text-white">
            <Wifi className="h-5 w-5" />
            <h2 className="text-lg font-semibold">Configurar conexión</h2>
          </div>
          <button onClick={handleSkip} className="text-white/80 hover:text-white">
            <X className="h-5 w-5" />
          </button>
        </div>
        <div className="p-6 space-y-4">
          {(step === "detect" || step === "input") && (
            <>
              <div className="text-center space-y-2">
                <div className="mx-auto w-16 h-16 rounded-full bg-primary-100 dark:bg-primary-900/30 flex items-center justify-center">
                  <Settings className="h-8 w-8 text-primary-600" />
                </div>
                <h3 className="text-xl font-bold text-secondary-900 dark:text-white">Conecta con tu servidor</h3>
                <p className="text-sm text-secondary-600 dark:text-secondary-400">
                  Detectamos que estás usando un dispositivo físico. Necesitas configurar la IP de tu PC.
                </p>
              </div>
              <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg p-3">
                <p className="text-xs text-amber-800 dark:text-amber-300">
                  <strong>Cómo obtener tu IP:</strong>
                  <br />
                  • Windows: <code>ipconfig</code> | Mac/Linux: <code>ifconfig</code>
                  <br />
                  • Busca la IP de tu red WiFi (ej. 192.168.1.50)
                </p>
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium text-secondary-700 dark:text-secondary-300">URL del backend</label>
                <input
                  type="text"
                  value={url}
                  onChange={(e) => {
                    setUrl(e.target.value);
                    setError(null);
                  }}
                  placeholder="http://192.168.1.50:8000"
                  className="w-full rounded-lg border border-secondary-300 dark:border-secondary-600 bg-white dark:bg-secondary-800 px-3 py-2 text-sm text-secondary-900 dark:text-white focus:border-primary-500 focus:ring-1 focus:ring-primary-500"
                />
                {error && <p className="text-xs text-red-600 dark:text-red-400">{error}</p>}
              </div>
              <button
                onClick={handleTest}
                disabled={!url.trim()}
                className="w-full flex items-center justify-center gap-2 rounded-lg bg-primary-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-primary-700 disabled:opacity-50"
              >
                Probar conexión <ArrowRight className="h-4 w-4" />
              </button>
              <button
                onClick={handleSkip}
                className="w-full text-sm text-secondary-500 hover:text-secondary-700 dark:text-secondary-400"
              >
                Omitir por ahora
              </button>
            </>
          )}
          {step === "test" && (
            <div className="text-center space-y-4 py-8">
              <div className="mx-auto w-12 h-12 rounded-full bg-primary-100 dark:bg-primary-900/30 flex items-center justify-center animate-pulse">
                <Wifi className="h-6 w-6 text-primary-600 animate-spin" />
              </div>
              <p className="text-secondary-600 dark:text-secondary-400">
                Probando conexión...
                <br />
                <code className="text-sm bg-secondary-100 dark:bg-secondary-800 px-1 py-0.5 rounded">{url}</code>
              </p>
            </div>
          )}
          {step === "success" && (
            <div className="text-center space-y-4 py-4">
              <div className="mx-auto w-16 h-16 rounded-full bg-green-100 dark:bg-green-900/30 flex items-center justify-center">
                <CheckCircle className="h-8 w-8 text-green-600" />
              </div>
              <h3 className="text-lg font-bold text-green-700 dark:text-green-400">¡Conexión exitosa!</h3>
              <p className="text-sm text-secondary-600 dark:text-secondary-400">Tu app está conectada al backend.</p>
              <button
                onClick={onComplete}
                className="w-full rounded-lg bg-primary-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-primary-700"
              >
                Empezar a usar la app
              </button>
            </div>
          )}
          {step === "error" && (
            <div className="text-center space-y-4 py-4">
              <div className="mx-auto w-16 h-16 rounded-full bg-red-100 dark:bg-red-900/30 flex items-center justify-center">
                <AlertCircle className="h-8 w-8 text-red-600" />
              </div>
              <h3 className="text-lg font-bold text-red-700 dark:text-red-400">Error de conexión</h3>
              <p className="text-sm text-secondary-600 dark:text-secondary-400 whitespace-pre-line">{error}</p>
              <div className="flex gap-2">
                <button
                  onClick={() => setStep("input")}
                  className="flex-1 rounded-lg bg-primary-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-primary-700"
                >
                  Intentar de nuevo
                </button>
                <button
                  onClick={handleSkip}
                  className="flex-1 rounded-lg border border-secondary-300 dark:border-secondary-600 px-4 py-2.5 text-sm font-medium text-secondary-700 dark:text-secondary-300 hover:bg-secondary-50 dark:hover:bg-secondary-800"
                >
                  Omitir
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export function useOnboarding() {
  const [showOnboarding, setShowOnboarding] = useState(false);
  const [isFirstLaunch, setIsFirstLaunch] = useState(false);

  useEffect(() => {
    const checkOnboarding = () => {
      if (typeof window === "undefined") return;
      if (!Capacitor.isNativePlatform()) return;
      if (Capacitor.getPlatform() !== "android") return;
      const hasShown = localStorage.getItem(HAS_SHOWN_ONBOARDING_KEY);
      const onboardingCompleted = localStorage.getItem(ONBOARDING_KEY);
      if (!hasShown || !onboardingCompleted) {
        setIsFirstLaunch(true);
        setShowOnboarding(true);
      }
    };
    const timer = setTimeout(checkOnboarding, 500);
    return () => clearTimeout(timer);
  }, []);

  const dismiss = () => setShowOnboarding(false);
  const complete = () => {
    setShowOnboarding(false);
    localStorage.setItem(ONBOARDING_KEY, "true");
    localStorage.setItem(HAS_SHOWN_ONBOARDING_KEY, "true");
  };

  return { showOnboarding, isFirstLaunch, dismiss, complete, OnboardingModal };
}
