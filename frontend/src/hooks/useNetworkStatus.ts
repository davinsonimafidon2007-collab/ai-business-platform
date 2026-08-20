"use client";

import { useEffect, useState } from "react";

export type NetworkStatus = "online" | "offline" | "unknown";

export interface NetworkStatusResult {
  isOnline: boolean;
  status: NetworkStatus;
  connectionType: string;
}

function getInitialOnlineStatus(): boolean {
  if (typeof window === "undefined") return true;
  return navigator.onLine;
}

export function useNetworkStatus(): NetworkStatusResult {
  const [isOnline, setIsOnline] = useState<boolean>(getInitialOnlineStatus);

  useEffect(() => {
    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);

    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);

    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  }, []);

  const status: NetworkStatus = isOnline ? "online" : "offline";
  const connectionType = isOnline ? "wifi" : "none";

  return { isOnline, status, connectionType };
}

export function offlineFetch<T>(
  fetcher: () => Promise<T>,
  staleData: T | null,
  isOnline: boolean
): Promise<T> {
  if (!isOnline && staleData !== null) {
    return Promise.resolve(staleData);
  }
  return fetcher();
}
