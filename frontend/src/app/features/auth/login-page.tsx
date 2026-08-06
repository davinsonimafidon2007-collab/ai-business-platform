"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Button } from "@/app/components/ui/button";
import { Input } from "@/app/components/ui/input";
import { useQueryClient } from "@tanstack/react-query";
import { api } from "@/app/services/api/client";
import { signInWithGoogle } from "@/app/services/google-auth";
import { useAuthStore } from "@/app/store/auth-store";
import type { AuthResponse, User } from "@/app/types/auth";

const loginSchema = z.object({
  email: z.string().email("Email inválido"),
  password: z.string().min(8, "Mínimo 8 caracteres"),
});

type LoginForm = z.infer<typeof loginSchema>;

export function LoginPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { setSession, isAuthenticated } = useAuthStore();
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isGoogleLoading, setIsGoogleLoading] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginForm>({
    resolver: zodResolver(loginSchema),
  });

  // Redirect to dashboard if already authenticated
  useEffect(() => {
    if (isAuthenticated) {
      router.push("/dashboard/");
    }
  }, [isAuthenticated, router]);

  const onSubmit = async (data: LoginForm) => {
    setIsLoading(true);
    setError(null);

    try {
      const authRes = await api.post<AuthResponse>("/auth/login", {
        email: data.email,
        password: data.password,
      });

      const userRes = await api.get<User>("/auth/me");
      // Persistencia unificada (tokens + user + store) en un solo lugar.
      setSession({
        accessToken: authRes.data.access_token,
        refreshToken: authRes.data.refresh_token,
        user: userRes.data,
      });

      // No mostrar datos en caché del usuario anterior tras este login.
      queryClient.clear();

      router.push("/dashboard/");
    } catch {
      setError("Credenciales inválidas");
    } finally {
      setIsLoading(false);
    }
  };

  const onGoogleLogin = async () => {
    setIsGoogleLoading(true);
    setError(null);
    try {
      await signInWithGoogle();
      // google-auth ya persiste via setSession; limpiamos caché de usuario previo.
      queryClient.clear();
      router.push("/dashboard/");
    } catch (err) {
      // eslint-disable-next-line no-console
      console.error("Google login failed:", err);
      setError("Error al iniciar sesión con Google");
    } finally {
      setIsGoogleLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <div className="w-full max-w-sm space-y-6">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-primary-600">AI Business</h1>
          <p className="mt-2 text-secondary-600 dark:text-secondary-400">
            Inicia sesión en tu cuenta
          </p>
        </div>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <Input
            id="email"
            label="Email"
            type="email"
            placeholder="tu@email.com"
            error={errors.email?.message}
            {...register("email")}
          />
          <Input
            id="password"
            label="Contraseña"
            type="password"
            placeholder="••••••••"
            error={errors.password?.message}
            {...register("password")}
          />

          {error && (
            <p className="text-sm text-error text-center">{error}</p>
          )}

          <Button type="submit" className="w-full" disabled={isLoading}>
            {isLoading ? "Iniciando sesión..." : "Iniciar sesión"}
          </Button>
        </form>

        <div className="relative my-4">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-secondary-200 dark:border-secondary-700"></div>
          </div>
          <div className="relative flex justify-center text-xs uppercase">
            <span className="bg-white px-2 text-secondary-500 dark:bg-secondary-900">
              O
            </span>
          </div>
        </div>

        <Button
          type="button"
          variant="outline"
          className="w-full"
          onClick={onGoogleLogin}
          disabled={isGoogleLoading}
        >
          {isGoogleLoading ? "Cargando..." : "Iniciar sesión con Google"}
        </Button>

        <p className="text-center text-sm text-secondary-500">
          ¿No tienes cuenta?{" "}
          <Link
            href="/auth/register/"
            className="text-primary-600 hover:text-primary-700"
          >
            Registrarse
          </Link>
        </p>
      </div>
    </div>
  );
}
