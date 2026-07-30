"use client";

import { useAuthStore } from "@/app/store/auth-store";
import { useThemeStore } from "@/app/store/theme-store";
import { Button } from "@/app/components/ui/button";
import { signOutOfGoogle } from "@/app/services/google-auth";

export function Navbar() {
  const { user, logout } = useAuthStore();
  const { theme, toggleTheme } = useThemeStore();

  const handleLogout = async () => {
    try {
      await signOutOfGoogle();
    } catch {
      // Ignore Firebase sign-out errors
    }
    logout();
  };

  return (
    <header className="sticky top-0 z-30 flex h-16 items-center justify-end gap-4 border-b border-secondary-200 bg-white/80 px-6 backdrop-blur-sm dark:border-secondary-700 dark:bg-secondary-900/80">
      <button
        onClick={toggleTheme}
        className="rounded-lg p-2 text-secondary-500 hover:bg-secondary-100 dark:hover:bg-secondary-800"
        aria-label="Toggle theme"
      >
        {theme === "dark" ? "☀️" : "🌙"}
      </button>

      {user && (
        <div className="flex items-center gap-3">
          <span className="text-sm text-secondary-600 dark:text-secondary-400">
            {user.full_name}
          </span>
          <Button variant="ghost" size="sm" onClick={handleLogout}>
            Cerrar sesión
          </Button>
        </div>
      )}
    </header>
  );
}
