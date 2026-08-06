import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { AuthGuard } from "@/app/components/auth/auth-guard";
import { useAuthStore } from "@/app/store/auth-store";
import type { User } from "@/app/types/auth";

const push = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
}));

const user: User = {
  id: "user-1",
  email: "user@example.com",
  full_name: "Test User",
  is_verified: true,
  role: "user",
  created_at: "2024-01-01T00:00:00Z",
};

describe("AuthGuard", () => {
  beforeEach(() => {
    push.mockClear();
    useAuthStore.setState({
      user: null,
      isAuthenticated: false,
      isLoading: true,
    });
  });

  it("muestra loading y NO redirige mientras isLoading", () => {
    render(
      <AuthGuard>
        <div>contenido protegido</div>
      </AuthGuard>
    );

    expect(screen.queryByText("contenido protegido")).toBeNull();
    expect(screen.getByText("Cargando...")).toBeInTheDocument();
    expect(push).not.toHaveBeenCalled();
  });

  it("redirige a login y no renderiza children cuando no está autenticado", () => {
    useAuthStore.setState({
      user: null,
      isAuthenticated: false,
      isLoading: false,
    });

    render(
      <AuthGuard>
        <div>contenido protegido</div>
      </AuthGuard>
    );

    expect(push).toHaveBeenCalledWith("/auth/login/");
    expect(screen.queryByText("contenido protegido")).toBeNull();
  });

  it("renderiza children cuando está autenticado", () => {
    useAuthStore.setState({
      user,
      isAuthenticated: true,
      isLoading: false,
    });

    render(
      <AuthGuard>
        <div>contenido protegido</div>
      </AuthGuard>
    );

    expect(screen.getByText("contenido protegido")).toBeInTheDocument();
    expect(push).not.toHaveBeenCalled();
  });
});
