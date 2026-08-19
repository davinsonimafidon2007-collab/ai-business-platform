import { describe, test, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import {
  SkeletonCard,
  ErrorState,
  EmptyState,
  OfflineBanner,
} from "@/components/ui/StateComponents";

describe("StateComponents", () => {
  test("SkeletonCard renders with accessible role", () => {
    render(<SkeletonCard lines={4} />);
    expect(screen.getByRole("status")).toBeInTheDocument();
    expect(screen.getByText("Cargando...")).toBeInTheDocument();
  });

  test("ErrorState renders title, message and handles retry", () => {
    const handleRetry = vi.fn();
    render(
      <ErrorState
        title="Error Personalizado"
        message="Detalle del error"
        onRetry={handleRetry}
      />
    );
    expect(screen.getByText("Error Personalizado")).toBeInTheDocument();
    expect(screen.getByText("Detalle del error")).toBeInTheDocument();

    const retryBtn = screen.getByRole("button", { name: /reintentar/i });
    fireEvent.click(retryBtn);
    expect(handleRetry).toHaveBeenCalledTimes(1);
  });

  test("EmptyState renders title, message and action button", () => {
    const handleAction = vi.fn();
    render(
      <EmptyState
        title="Sin elementos"
        message="No hay datos registrados."
        action={{ label: "Crear uno", onClick: handleAction }}
      />
    );
    expect(screen.getByText("Sin elementos")).toBeInTheDocument();
    expect(screen.getByText("No hay datos registrados.")).toBeInTheDocument();

    const actionBtn = screen.getByRole("button", { name: /crear uno/i });
    fireEvent.click(actionBtn);
    expect(handleAction).toHaveBeenCalledTimes(1);
  });

  test("OfflineBanner renders warning text", () => {
    render(<OfflineBanner />);
    expect(
      screen.getByText(/No tienes conexión a internet/i)
    ).toBeInTheDocument();
  });
});
