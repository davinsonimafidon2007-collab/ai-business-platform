import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useLogout } from "@/app/hooks/use-logout";
import { useAuthStore, TOKEN_KEYS } from "@/app/store/auth-store";
import type { User } from "@/app/types/auth";

vi.mock("@/app/services/google-auth", () => ({
  signOutOfGoogle: vi.fn().mockResolvedValue(undefined),
}));

import { signOutOfGoogle } from "@/app/services/google-auth";

const user: User = {
  id: "user-1",
  email: "user@example.com",
  full_name: "Test User",
  is_verified: true,
  role: "user",
  created_at: "2024-01-01T00:00:00Z",
};

const createWrapper = () => {
  const queryClient = new QueryClient();
  const Wrapper = ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
  Wrapper.displayName = "QueryClientWrapper";
  return { Wrapper, queryClient };
};

describe("useLogout", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.localStorage.clear();
    useAuthStore.setState({
      user: null,
      isAuthenticated: false,
      isLoading: false,
    });
  });

  it("vacía la caché de React Query y resetea store + localStorage", async () => {
    const { Wrapper, queryClient } = createWrapper();
    queryClient.setQueryData(["vehicles"], [{ id: "1" }]);
    await useAuthStore
      .getState()
      .setSession({ accessToken: "at", refreshToken: "rt", user });

    const { result } = renderHook(() => useLogout(), { wrapper: Wrapper });

    await act(async () => {
      await result.current();
    });

    expect(signOutOfGoogle).toHaveBeenCalled();
    expect(queryClient.getQueryData(["vehicles"])).toBeUndefined();
    expect(useAuthStore.getState().isAuthenticated).toBe(false);
    expect(useAuthStore.getState().user).toBeNull();
    expect(window.localStorage.getItem(TOKEN_KEYS.accessToken)).toBeNull();
    expect(window.localStorage.getItem(TOKEN_KEYS.refreshToken)).toBeNull();
    expect(window.localStorage.getItem(TOKEN_KEYS.user)).toBeNull();
  });
});
