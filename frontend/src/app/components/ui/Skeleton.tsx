"use client";

import { cn } from "@/app/utils/cn";

interface SkeletonProps {
  className?: string;
}

export function Skeleton({ className }: SkeletonProps) {
  return (
    <div
      className={cn("animate-pulse rounded-md bg-secondary-200 dark:bg-secondary-700", className)}
      aria-hidden="true"
    />
  );
}

export function SkeletonRow({ className }: SkeletonProps) {
  return (
    <div
      className={cn(
        "flex items-center gap-3 rounded-2xl border border-secondary-200 bg-white p-4 dark:border-primary-900/40 dark:bg-secondary-900",
        className
      )}
    >
      <Skeleton className="h-10 w-10 flex-none rounded-xl" />
      <div className="flex-1 space-y-2">
        <Skeleton className="h-3 w-2/3" />
        <Skeleton className="h-2.5 w-1/3" />
      </div>
    </div>
  );
}

export function SkeletonCard({ className }: SkeletonProps) {
  return (
    <div
      className={cn(
        "rounded-2xl border border-secondary-200 bg-white p-5 dark:border-primary-900/40 dark:bg-secondary-900",
        className
      )}
    >
      <Skeleton className="h-4 w-1/2" />
      <Skeleton className="mt-3 h-3 w-3/4" />
      <Skeleton className="mt-2 h-3 w-2/3" />
    </div>
  );
}
