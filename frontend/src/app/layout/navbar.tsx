"use client";

import { useAuthStore } from "@/app/store/auth-store";
import { useThemeStore } from "@/app/store/theme-store";
import { Button } from "@/app/components/ui/button";
import { useLogout } from "@/app/hooks/use-logout";
import { isAuthDisabled } from "@/app/config/app-mode";

export function Navbar() {
  const user = useAuthStore((state) => state.user);
  const { theme, toggleTheme } = useThemeStore();
  const logout = useLogout();
  const authDisabled = isAuthDisabled();

  return (
    <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-secondary-200 bg-white/80 px-6 backdrop-blur-sm dark:border-secondary-800 dark:bg-secondary-900/80">
      <div className="flex items-center gap-4">
        <h2 className="text-sm font-medium text-secondary-500 dark:text-secondary-400">
          Plataforma de Orquestación de Agentes de IA
        </h2>
      </div>
      <div className="flex items-center gap-3">
        <button className="relative rounded-lg p-2 text-secondary-500 hover:bg-secondary-100 dark:hover:bg-secondary-800">
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0118 9.75v-.7V9A6 6 0 006 9v.75a8.967 8.967 0 01-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 01-5.714 0m5.714 0a3 3 0 11-5.714 0" />
          </svg>
        </button>
        <button
          onClick={toggleTheme}
          className="rounded-lg p-2 text-secondary-500 hover:bg-secondary-100 dark:hover:bg-secondary-800"
          aria-label="Toggle theme"
        >
          {theme === "dark" ? (
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 3v2.25m6.364.386l-1.591 1.591M21 12h-2.25m-.386 6.364l-1.591-1.591M12 18.75V21m-4.773-4.227l-1.591 1.591M5.25 12H3m4.227-4.773L5.636 5.636M15.75 12a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0z" />
            </svg>
          ) : (
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M21.752 15.002A9.718 9.718 0 0118 15.75c-5.385 0-9.75-4.365-9.75-9.75 0-1.33.266-2.597.748-3.752A9.753 9.753 0 003 11.25C3 16.635 7.365 21 12.75 21a9.753 9.753 0 009.002-5.998z" />
            </svg>
          )}
        </button>
        {user && !authDisabled && (
          <Button variant="ghost" size="sm" onClick={() => void logout()}>
            Cerrar sesión
          </Button>
        )}
      </div>
    </header>
  );
}
