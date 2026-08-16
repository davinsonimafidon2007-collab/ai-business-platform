"use client";

import { useEffect, useState, useCallback } from "react";
import { cn } from "@/app/utils/cn";
import { CheckCircle2, AlertTriangle, Info, X, Loader2 } from "lucide-react";

export type ToastType = "success" | "error" | "warning" | "info" | "loading";

interface ToastProps {
  id: string;
  type: ToastType;
  title: string;
  message?: string;
  duration?: number;
  onClose: (id: string) => void;
}

const config: Record<ToastType, { icon: typeof CheckCircle2; bg: string; border: string; text: string }> = {
  success: {
    icon: CheckCircle2,
    bg: "bg-green-400/10",
    border: "border-green-400/20",
    text: "text-green-400",
  },
  error: {
    icon: AlertTriangle,
    bg: "bg-red-400/10",
    border: "border-red-400/20",
    text: "text-red-400",
  },
  warning: {
    icon: AlertTriangle,
    bg: "bg-yellow-400/10",
    border: "border-yellow-400/20",
    text: "text-yellow-400",
  },
  info: {
    icon: Info,
    bg: "bg-primary-400/10",
    border: "border-primary-400/20",
    text: "text-primary-400",
  },
  loading: {
    icon: Loader2,
    bg: "bg-blue-400/10",
    border: "border-blue-400/20",
    text: "text-blue-400",
  },
};

export function Toast({ id, type, title, message, duration = 5000, onClose }: ToastProps) {
  const [progress, setProgress] = useState(100);
  const [visible, setVisible] = useState(false);
  const { icon: Icon, bg, border, text } = config[type] || config.info;
  const isLoading = type === "loading";

  const handleClose = useCallback(() => {
    setVisible(false);
    setTimeout(() => onClose(id), 300);
  }, [id, onClose]);

  useEffect(() => {
    const enterTimer = setTimeout(() => setVisible(true), 10);
    return () => clearTimeout(enterTimer);
  }, []);

  useEffect(() => {
    if (isLoading || duration === Infinity) return;

    const startTime = Date.now();
    const interval = setInterval(() => {
      const elapsed = Date.now() - startTime;
      const remaining = Math.max(0, 100 - (elapsed / duration) * 100);
      setProgress(remaining);
      if (remaining <= 0) {
        clearInterval(interval);
        handleClose();
      }
    }, 16);

    return () => clearInterval(interval);
  }, [duration, isLoading, handleClose]);

  return (
    <div
      className={cn(
        "relative flex items-start gap-3 p-4 rounded-xl border backdrop-blur-sm shadow-lg transition-all duration-300 min-w-[320px] max-w-[420px]",
        bg,
        border,
        visible ? "translate-x-0 opacity-100" : "translate-x-full opacity-0"
      )}
    >
      <Icon className={cn("w-5 h-5 shrink-0 mt-0.5", text, isLoading && "animate-spin")} />
      <div className="flex-1 min-w-0">
        <p className="text-sm font-semibold text-white">{title}</p>
        {message && <p className="text-xs text-secondary-400 mt-0.5 leading-relaxed">{message}</p>}
      </div>
      {!isLoading && (
        <button
          onClick={handleClose}
          className="p-1 rounded text-secondary-500 hover:text-white hover:bg-white/5 transition-colors shrink-0"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      )}

      {/* Progress bar */}
      {!isLoading && duration !== Infinity && (
        <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-white/5 rounded-b-xl overflow-hidden">
          <div
            className={cn("h-full transition-all duration-100", text.replace("text-", "bg-"))}
            style={{ width: `${progress}%` }}
          />
        </div>
      )}
    </div>
  );
}
