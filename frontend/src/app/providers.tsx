"use client";

import { QueryClient, QueryClientProvider, useQueryClient } from "@tanstack/react-query";
import { useState, useEffect } from "react";
import { useAuthStore } from "@/app/store/auth-store";
import { useThemeStore } from "@/app/store/theme-store";
import { initGoogleAuth } from "@/app/services/google-auth";
import { initPushNotifications } from "@/app/services/push-notifications";
import { initLocalNotifications } from "@/app/services/local-notifications.service";
import { isAuthDisabled } from "@/app/config/app-mode";
import { useAndroidBackButton } from "@/app/hooks/useAndroidBackButton";
import { useOnboarding, OnboardingModal } from "@/app/hooks/use-onboarding";
import { NotificationNavigator } from "@/app/hooks/notification-navigation";
import { useServiceWorker } from "@/app/hooks/use-service-worker";

function ThemeInitializer({ children }: { children: React.ReactNode }) {
  const initialize = useThemeStore((state) => state.initialize);

  useEffect(() => {
    initialize();
  }, [initialize]);

  return <>{children}</>;
}

function PushNotificationsInitializer({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    initPushNotifications();
  }, []);

  return <>{children}</>;
}

function LocalNotificationsInitializer({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    initLocalNotifications();
  }, []);

  return <>{children}</>;
}

function AuthInitializer({ children }: { children: React.ReactNode }) {
  const initialize = useAuthStore((state) => state.initialize);
  const logout = useAuthStore((state) => state.logout);
  const queryClient = useQueryClient();

  useEffect(() => {
    initialize();

    // Escucha el evento "auth:logout" que emite el API client cuando un refresh
    // falla (401). Evita importar el store desde el client (sin dependencia
    // circular) y garantiza que store + query cache queden coherentes.
    const onAuthLogout = () => {
      queryClient.clear();
      logout();
    };
    window.addEventListener("auth:logout", onAuthLogout);
    return () => window.removeEventListener("auth:logout", onAuthLogout);
  }, [initialize, logout, queryClient]);

  return <>{children}</>;
}

function GoogleAuthInitializer({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    // Auth desactivada (uso personal): no inicializar Firebase/Google Login.
    if (!isAuthDisabled()) {
      initGoogleAuth();
    }
  }, []);

  return <>{children}</>;
}

/**
 * Mounts native-app navigation effects (Android hardware back button) a single
 * time, at the top of the provider tree. Do NOT re-mount per page to avoid
 * duplicate listeners.
 */
function NativeNavigationEffects({ children }: { children: React.ReactNode }) {
  useAndroidBackButton();
  return <>{children}</>;
}

/**
 * MOB-P1-003: Wrapper del onboarding de configuración de URL.
 */
function OnboardingWrapper({ children }: { children: React.ReactNode }) {
  const { showOnboarding, complete, dismiss } = useOnboarding();
  return (
    <>
      {children}
      {showOnboarding && <OnboardingModal onComplete={complete} onDismiss={dismiss} />}
    </>
  );
}

/**
 * MOB-P2-006 / TASK-016: Registra el Service Worker (offline support) una vez.
 */
function ServiceWorkerInitializer({ children }: { children: React.ReactNode }) {
  useServiceWorker();
  return <>{children}</>;
}

/**
 * MOB-P2-006: Escucha el evento `deepLink:navigate` emitido por push
 * notifications (MOB-P1-009 / MOB-P2-006) y navega a la ruta resuelta.
 */
function NotificationListener({ children }: { children: React.ReactNode }) {
  return <NotificationNavigator>{children}</NotificationNavigator>;
}

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 60 * 1000,
            retry: 1,
            refetchOnWindowFocus: false,
          },
        },
      })
  );

  return (
    <QueryClientProvider client={queryClient}>
      <ThemeInitializer>
        <AuthInitializer>
          <GoogleAuthInitializer>
            <PushNotificationsInitializer>
              <LocalNotificationsInitializer>
                <NativeNavigationEffects>
                  <NotificationListener>
                    <OnboardingWrapper>
                      <ServiceWorkerInitializer>{children}</ServiceWorkerInitializer>
                    </OnboardingWrapper>
                  </NotificationListener>
                </NativeNavigationEffects>
              </LocalNotificationsInitializer>
            </PushNotificationsInitializer>
          </GoogleAuthInitializer>
        </AuthInitializer>
      </ThemeInitializer>
    </QueryClientProvider>
  );
}