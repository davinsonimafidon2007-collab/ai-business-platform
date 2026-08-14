"use client";

/**
 * MOB-P1-004: Componentes de estado reutilizables
 * EmptyState, LoadingState, ErrorState, SkeletonList, DataState
 */

import { ReactNode } from "react";
import { Search, AlertCircle, Loader2, Inbox, Car, TrendingUp, History, Settings } from "lucide-react";
import { Button } from "@/app/components/ui/button";

interface LoadingStateProps {
  message?: string;
  fullPage?: boolean;
  className?: string;
}
export function LoadingState({ message = "Cargando...", fullPage = false, className = "" }: LoadingStateProps) {
  const wrapperClass = fullPage
    ? "flex flex-col items-center justify-center min-h-[60vh]"
    : "flex flex-col items-center justify-center py-12";
  return (
    <div className={`${wrapperClass} ${className}`}>
      <Loader2 className="h-8 w-8 animate-spin text-primary-600 mb-3" />
      <p className="text-sm text-secondary-500 dark:text-secondary-400">{message}</p>
    </div>
  );
}

interface ErrorStateProps {
  title?: string;
  message?: string;
  onRetry?: () => void;
  fullPage?: boolean;
  className?: string;
}
export function ErrorState({
  title = "Algo salió mal",
  message = "No pudimos cargar los datos.",
  onRetry,
  fullPage = false,
  className = "",
}: ErrorStateProps) {
  const wrapperClass = fullPage
    ? "flex flex-col items-center justify-center min-h-[60vh] px-4"
    : "flex flex-col items-center justify-center py-12 px-4";
  return (
    <div className={`${wrapperClass} ${className}`}>
      <div className="w-14 h-14 rounded-full bg-red-100 dark:bg-red-900/30 flex items-center justify-center mb-3">
        <AlertCircle className="h-7 w-7 text-red-600" />
      </div>
      <h3 className="text-base font-semibold text-secondary-900 dark:text-white mb-1">{title}</h3>
      <p className="text-sm text-secondary-500 dark:text-secondary-400 text-center max-w-xs mb-4">{message}</p>
      {onRetry && (
        <Button variant="outline" size="sm" onClick={onRetry}>
          Intentar de nuevo
        </Button>
      )}
    </div>
  );
}

interface EmptyStateProps {
  icon?: "search" | "car" | "trending" | "history" | "settings" | "inbox";
  title: string;
  description?: string;
  action?: { label: string; onClick: () => void };
  fullPage?: boolean;
  className?: string;
}
const iconMap = { search: Search, car: Car, trending: TrendingUp, history: History, settings: Settings, inbox: Inbox };
export function EmptyState({
  icon = "inbox",
  title,
  description,
  action,
  fullPage = false,
  className = "",
}: EmptyStateProps) {
  const Icon = iconMap[icon];
  const wrapperClass = fullPage
    ? "flex flex-col items-center justify-center min-h-[60vh] px-4"
    : "flex flex-col items-center justify-center py-12 px-4";
  return (
    <div className={`${wrapperClass} ${className}`}>
      <div className="w-14 h-14 rounded-full bg-secondary-100 dark:bg-secondary-800 flex items-center justify-center mb-3">
        <Icon className="h-7 w-7 text-secondary-400" />
      </div>
      <h3 className="text-base font-semibold text-secondary-900 dark:text-white mb-1">{title}</h3>
      {description && (
        <p className="text-sm text-secondary-500 dark:text-secondary-400 text-center max-w-xs mb-4">{description}</p>
      )}
      {action && (
        <Button size="sm" onClick={action.onClick}>
          {action.label}
        </Button>
      )}
    </div>
  );
}

interface SkeletonProps {
  count?: number;
  className?: string;
}
export function SkeletonRow({ className = "" }: { className?: string }) {
  return (
    <div className={`animate-pulse flex items-center gap-3 p-3 rounded-lg bg-secondary-50 dark:bg-secondary-800/50 ${className}`}>
      <div className="h-10 w-10 rounded-full bg-secondary-200 dark:bg-secondary-700" />
      <div className="flex-1 space-y-2">
        <div className="h-3 w-3/4 rounded bg-secondary-200 dark:bg-secondary-700" />
        <div className="h-2 w-1/2 rounded bg-secondary-200 dark:bg-secondary-700" />
      </div>
    </div>
  );
}
export function SkeletonList({ count = 5, className = "" }: SkeletonProps) {
  return (
    <div className={`space-y-2 ${className}`}>
      {Array.from({ length: count }).map((_, i) => (
        <SkeletonRow key={i} />
      ))}
    </div>
  );
}

interface DataStateProps<T> {
  isLoading: boolean;
  isError: boolean;
  data: T[] | undefined;
  error?: Error | null;
  children: (data: T[]) => ReactNode;
  emptyProps?: Omit<EmptyStateProps, "fullPage">;
  loadingMessage?: string;
  errorMessage?: string;
  onRetry?: () => void;
  fullPage?: boolean;
  className?: string;
}
export function DataState<T>({
  isLoading,
  isError,
  data,
  error,
  children,
  emptyProps,
  loadingMessage,
  errorMessage,
  onRetry,
  fullPage = false,
  className = "",
}: DataStateProps<T>) {
  if (isLoading)
    return <LoadingState message={loadingMessage} fullPage={fullPage} className={className} />;
  if (isError)
    return (
      <ErrorState
        title="Error al cargar"
        message={errorMessage || error?.message || "No pudimos cargar los datos."}
        onRetry={onRetry}
        fullPage={fullPage}
        className={className}
      />
    );
  if (!data || data.length === 0)
    return (
      <EmptyState
        {...(emptyProps || {
          icon: "inbox",
          title: "No hay datos",
          description: "Aún no hay información para mostrar.",
        })}
        fullPage={fullPage}
        className={className}
      />
    );
  return <>{children(data)}</>;
}
