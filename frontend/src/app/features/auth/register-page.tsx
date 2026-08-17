"use client";

import { useState } from "react";
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

// El backend exige min_length=8 en RegisterRequest (ver app/schemas/auth.py).
const registerSchema = z
  .object({
    email: z.string().email("Email inválido"),
    password: z.string().min(8, "Mínimo 8 caracteres"),
    confirmPassword: z.string().min(8, "Mínimo 8 caracteres"),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: "Las contraseñas no coinciden",
    path: ["confirmPassword"],
  });

type RegisterForm = z.infer<typeof registerSchema>;

export function RegisterPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { setSession } = useAuthStore();
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isGoogleLoading, setIsGoogleLoading] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<RegisterForm>({
    resolver: zodResolver(registerSchema),
  });

  const onSubmit = async (data: RegisterForm) => {
    setIsLoading(true);
    setError(null);

    try {
      // 1. Crear la cuenta.
      await api.post("/auth/register", {
        email: data.email,
        password: data.password,
      });

      // 2. El endpoint de registro solo devuelve el usuario creado, no tokens
      //    (ver app/api/v1/auth.py), así que iniciamos sesión justo después
      //    para no obligar al usuario a escribir sus datos dos veces.
      const authRes = await api.post<AuthResponse>("/auth/login", {
        email: data.email,
        password: data.password,
      });

      const userRes = await api.get<User>("/auth/me");
      // Persistencia unificada (tokens + user + store) en un solo lugar.
      await setSession({
        accessToken: authRes.data.access_token,
        refreshToken: authRes.data.refresh_token,
        user: userRes.data,
      });

      // Evitar mostrar datos en caché de un usuario previo.
      queryClient.clear();

      router.push("/dashboard/");
    } catch {
      setError("No se pudo crear la cuenta. Prueba con otro email.");
    } finally {
      setIsLoading(false);
    }
  };

  const onGoogleRegister = async () => {
    setIsGoogleLoading(true);
    setError(null);
    try {
      // authenticate_with_google crea el usuario automáticamente si no existe
      // (ver app/services/auth_service.py), así que sirve igual para registro.
      await signInWithGoogle();
      // google-auth ya persiste via setSession; limpiamos caché de usuario previo.
      queryClient.clear();
      router.push("/dashboard/");
    } catch {
      setError("Error al registrarse con Google");
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
            Crea tu cuenta
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
          <Input
            id="confirmPassword"
            label="Confirmar contraseña"
            type="password"
            placeholder="••••••••"
            error={errors.confirmPassword?.message}
            {...register("confirmPassword")}
          />

          {error && (
            <p className="text-sm text-error text-center">{error}</p>
          )}

          <Button type="submit" className="w-full" disabled={isLoading}>
            {isLoading ? "Creando cuenta..." : "Registrarse"}
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
          onClick={onGoogleRegister}
          disabled={isGoogleLoading}
        >
          {isGoogleLoading ? "Cargando..." : "Registrarse con Google"}
        </Button>

        <p className="text-center text-sm text-secondary-500">
          ¿Ya tienes cuenta?{" "}
          <Link
            href="/auth/login/"
            className="text-primary-600 hover:text-primary-700"
          >
            Iniciar sesión
          </Link>
        </p>
      </div>
    </div>
  );
}
