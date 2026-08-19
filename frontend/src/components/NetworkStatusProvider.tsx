"use client";

import React from "react";
import { OfflineBanner } from "@/components/ui/StateComponents";
import { useNetworkStatus } from "@/hooks/useNetworkStatus";

export function NetworkStatusProvider({ children }: { children: React.ReactNode }) {
  const { isOnline } = useNetworkStatus();

  return (
    <>
      {!isOnline && <OfflineBanner />}
      <div className={!isOnline ? "mt-10" : ""}>
        {children}
      </div>
    </>
  );
}
