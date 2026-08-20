"use client";

import React from "react";
import { AlertCircle, RefreshCw, Inbox, WifiOff } from "lucide-react";
import { useNetworkStatus } from "@/hooks/useNetworkStatus";

// --- LOADING SKELETON ---
export const SkeletonCard = ({ lines = 3 }: { lines?: number }) => (
  <div
    className="animate-pulse space-y-3 p-4 border rounded-lg bg-white dark:bg-gray-900 border-gray-200 dark:border-gray-800"
    role="status"
    aria-label="Cargando contenido"
  >
    <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-3/4"></div>
    {Array.from({ length: lines }).map((_, i) => (
      <div key={i} className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-full"></div>
    ))}
    <span className="sr-only">Cargando...</span>
  </div>
);

// --- ERROR STATE ---
interface ErrorStateProps {
  title?: string;
  message: string;
  onRetry?: () => void;
}
export const ErrorState: React.FC<ErrorStateProps> = ({
  title = "Algo salió mal",
  message,
  onRetry,
}) => (
  <div
    className="flex flex-col items-center justify-center p-8 text-center border border-red-200 dark:border-red-900 rounded-lg bg-red-50 dark:bg-red-950/20"
    role="alert"
  >
    <AlertCircle className="w-12 h-12 text-red-500 mb-4" aria-hidden="true" />
    <h3 className="text-lg font-semibold text-red-800 dark:text-red-200">{title}</h3>
    <p className="text-sm text-red-600 dark:text-red-300 mt-2 max-w-md">{message}</p>
    {onRetry && (
      <button
        onClick={onRetry}
        className="mt-4 flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-md hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2 transition-colors"
        aria-label="Reintentar acción"
      >
        <RefreshCw className="w-4 h-4" aria-hidden="true" />
        Reintentar
      </button>
    )}
  </div>
);

// --- EMPTY STATE ---
interface EmptyStateProps {
  icon?: React.ReactNode;
  title: string;
  message: string;
  action?: { label: string; onClick: () => void };
}
export const EmptyState: React.FC<EmptyStateProps> = ({
  icon = <Inbox className="w-12 h-12 text-gray-400" />,
  title,
  message,
  action,
}) => (
  <div className="flex flex-col items-center justify-center p-8 text-center border border-gray-200 dark:border-gray-800 rounded-lg bg-gray-50 dark:bg-gray-900/50">
    <div className="mb-4" aria-hidden="true">
      {icon}
    </div>
    <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100">{title}</h3>
    <p className="text-sm text-gray-500 dark:text-gray-400 mt-2 max-w-md">{message}</p>
    {action && (
      <button
        onClick={action.onClick}
        className="mt-4 px-4 py-2 text-sm font-medium text-white bg-primary-600 rounded-md hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 transition-colors"
      >
        {action.label}
      </button>
    )}
  </div>
);

// --- OFFLINE BANNER ---
export const OfflineBanner = () => {
  const { isOnline } = useNetworkStatus();
  if (isOnline) return null;

  return (
    <div
      className="fixed top-0 left-0 right-0 z-50 flex items-center justify-center gap-2 px-4 py-2 text-sm font-medium text-white bg-yellow-600 shadow-md"
      role="status"
    >
      <WifiOff className="w-4 h-4" aria-hidden="true" />
      <span>No tienes conexión a internet. Algunas funciones pueden no estar disponibles.</span>
    </div>
  );
};
