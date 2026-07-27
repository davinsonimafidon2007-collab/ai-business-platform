"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Button } from "@/app/components/ui/button";
import { Input } from "@/app/components/ui/input";
import { api } from "@/app/services/api/client";
import { useAuthStore } from "@/app/store/auth-store";
import type { AuthResponse, User } from "@/app/types/auth";

const loginSchema = z.object({
  email: z.string().email("Email inválido"),
  password: z.string().min(6, "Mínimo 6 caracteres"),
});

type LoginForm = z.infer<typeof loginSchema>;

export function LoginPage() {
  const router = useRouter();
  const { setUser } = useAuthStore();
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginForm>({
    resolver: zodResolver(loginSchema),
  });

  const onSubmit = async (data: LoginForm) => {
    setIsLoading(true);
    setError(null);

    try {
      const authRes = await api.post<AuthResponse>("/auth/login", {
        email: data.email,
        password: data.password,
      });

      localStorage.setItem("access_token", authRes.data.access_token);
      localStorage.setItem("refresh_token", authRes.data.refresh_token);

      const userRes = await api.get<User>("/auth/me");
      localStorage.setItem("user", JSON.stringify(userRes.data));
      setUser(userRes.data);

      router.push("/dashboard");
    } catch {
      setError("Credenciales inválidas");
    } finally {
      setIsLoading(false);
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

        <p className="text-center text-sm text-secondary-500">
          ¿No tienes cuenta?{" "}
          <Link
            href="/auth/register"
            className="text-primary-600 hover:text-primary-700"
          >
            Registrarse
          </Link>
        </p>
      </div>
    </div>
  );
}