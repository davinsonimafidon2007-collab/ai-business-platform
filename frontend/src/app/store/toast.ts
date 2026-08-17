import { create } from "zustand";
import { ToastItem } from "@/app/components/ui/ToastContainer";
import { ToastType } from "@/app/components/ui/Toast";

interface ToastStore {
  toasts: ToastItem[];
  addToast: (toast: Omit<ToastItem, "id">) => string;
  removeToast: (id: string) => void;
  updateToast: (id: string, updates: Partial<ToastItem>) => void;
}

let toastIdCounter = 0;

export const useToastStore = create<ToastStore>((set) => ({
  toasts: [],

  addToast: (toast) => {
    const id = `toast-${++toastIdCounter}-${Date.now()}`;
    set((state) => ({
      toasts: [...state.toasts, { ...toast, id }],
    }));
    return id;
  },

  removeToast: (id) => {
    set((state) => ({
      toasts: state.toasts.filter((t) => t.id !== id),
    }));
  },

  updateToast: (id, updates) => {
    set((state) => ({
      toasts: state.toasts.map((t) => (t.id === id ? { ...t, ...updates } : t)),
    }));
  },
}));

// Helper hooks/functions
export function toast(type: ToastType, title: string, message?: string, duration?: number) {
  return useToastStore.getState().addToast({ type, title, message, duration });
}

export function toastSuccess(title: string, message?: string) {
  return toast("success", title, message, 4000);
}

export function toastError(title: string, message?: string) {
  return toast("error", title, message, 6000);
}

export function toastWarning(title: string, message?: string) {
  return toast("warning", title, message, 5000);
}

export function toastInfo(title: string, message?: string) {
  return toast("info", title, message, 4000);
}

export function toastLoading(title: string, message?: string) {
  return toast("loading", title, message, Infinity);
}

export function dismissToast(id: string) {
  useToastStore.getState().removeToast(id);
}

export function updateToast(id: string, type: ToastType, title: string, message?: string) {
  useToastStore.getState().updateToast(id, { type, title, message, duration: type === "loading" ? Infinity : 4000 });
}
