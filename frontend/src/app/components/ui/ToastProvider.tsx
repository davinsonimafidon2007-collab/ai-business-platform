"use client";

import { useToastStore } from "@/app/store/toast";
import { ToastContainer } from "./ToastContainer";

export function ToastProvider() {
  const toasts = useToastStore((s) => s.toasts);
  const removeToast = useToastStore((s) => s.removeToast);

  return <ToastContainer toasts={toasts} onClose={removeToast} />;
}
