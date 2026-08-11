"use client";

import { useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import { Capacitor } from "@capacitor/core";
import { App } from "@capacitor/app";

let navigatedInApp = false;

function trackNavigation() {
  if (typeof window === "undefined") return;
  const pushState = history.pushState;
  history.pushState = function (...args) {
    navigatedInApp = true;
    return pushState.apply(this, args);
  };
}

export function useNativeBackButton() {
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (!Capacitor.isNativePlatform()) return;

    trackNavigation();

    const listener = App.addListener("backButton", ({ canGoBack }) => {
      if (navigatedInApp) {
        navigatedInApp = false;
        router.back();
        return;
      }
      if (pathname && pathname !== "/" && !pathname.startsWith("/auth/")) {
        router.push("/");
        return;
      }
      if (canGoBack) {
        window.history.back();
      } else {
        void App.minimizeApp();
      }
    });

    return () => {
      void listener.then((l) => l.remove());
    };
  }, [router, pathname]);
}
