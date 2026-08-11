"use client";

import { Sidebar } from "@/app/layout/sidebar";
import { Navbar } from "@/app/layout/navbar";
import { MobileTabBar } from "@/app/layout/MobileTabBar";
import { useIsMobile } from "@/app/hooks/useIsMobile";
import { useThemeStore } from "@/app/store/theme-store";
import { useAuthStore } from "@/app/store/auth-store";
import { Button } from "@/app/components/ui/button";
import { useLogout } from "@/app/hooks/use-logout";
import { isAuthDisabled } from "@/app/config/app-mode";
import { Moon, Sun, LogOut } from "lucide-react";

/** Cabecera compacta para el shell móvil (mantiene tema + logout). */
function MobileHeader() {
  const { theme, toggleTheme } = useThemeStore();
  const user = useAuthStore((s) => s.user);
  const logout = useLogout();
  const authDisabled = isAuthDisabled();

  return (
    <header className="sticky top-0 z-40 flex h-14 items-center justify-between border-b border-secondary-200 bg-white/90 px-4 backdrop-blur dark:border-primary-900/30 dark:bg-secondary-900/90">
      <p className="text-sm font-semibold text-secondary-900 dark:text-primary-100">
        AI Business
      </p>
      <div className="flex items-center gap-1">
        <button
          onClick={toggleTheme}
          className="rounded-lg p-2 text-secondary-500 hover:bg-secondary-100 dark:hover:bg-secondary-800"
          aria-label="Toggle theme"
        >
          {theme === "dark" ? (
            <Sun className="h-5 w-5" />
          ) : (
            <Moon className="h-5 w-5" />
          )}
        </button>
        {user && !authDisabled && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => void logout()}
            className="h-9 gap-1 px-2 text-xs"
          >
            <LogOut className="h-4 w-4" />
            Cerrar
          </Button>
        )}
      </div>
    </header>
  );
}

/**
 * MOBILE.SHELL.1 — AppShell compartido.
 *
 * En móvil/nativo renderiza cabecera compacta + contenido a ancho completo
 * + bottom tabs (sin Sidebar ni pl-64). En desktop mantiene Sidebar + Navbar.
 */
export function AppShell({ children }: { children: React.ReactNode }) {
  const mobile = useIsMobile();

  if (mobile) {
    return (
      <div className="flex min-h-dvh flex-col bg-secondary-50 dark:bg-secondary-950">
        <MobileHeader />
        <main className="flex-1 px-4 pb-24 pt-3">{children}</main>
        <MobileTabBar />
      </div>
    );
  }

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <div className="flex flex-1 flex-col md:pl-64">
        <Navbar />
        <main className="flex-1 p-6">{children}</main>
      </div>
    </div>
  );
}