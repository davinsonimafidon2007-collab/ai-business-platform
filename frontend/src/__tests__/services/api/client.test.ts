import { describe, it, expect, vi, beforeEach } from "vitest";

// Determinamos la base URL por el camino "web" (sin NEXT_PUBLIC_API_URL).
process.env.NEXT_PUBLIC_API_URL = "";

const { requestUseMock, responseUseMock, postMock, createMock } = vi.hoisted(
  () => ({
    requestUseMock: vi.fn(),
    responseUseMock: vi.fn(),
    postMock: vi.fn(),
    createMock: vi.fn(),
  })
);

vi.mock("axios", () => {
  // La "instancia" de axios es un callable (función) con interceptores, para
  // poder cubrir el retry `this.client(originalRequest)` de handleError.
  const makeInstance = () => {
    const instance: any = vi.fn(async () => ({ data: "retried" }));
    instance.interceptors = {
      request: { use: requestUseMock },
      response: { use: responseUseMock },
    };
    return instance;
  };
  createMock.mockImplementation(makeInstance);
  return {
    default: { create: createMock, post: postMock },
    AxiosError: class AxiosError extends Error {},
  };
});

vi.mock("@capacitor/core", () => ({
  Capacitor: {
    isNativePlatform: vi.fn().mockReturnValue(false),
    getPlatform: vi.fn().mockReturnValue("web"),
  },
}));
vi.mock("@/app/config/app-mode", () => ({
  isAuthDisabled: vi.fn().mockReturnValue(false),
}));

import { apiClient, api } from "@/app/services/api/client";
import { isAuthDisabled } from "@/app/config/app-mode";
import { secureStorage } from "@/app/services/storage";

// Los interceptores se registran en el constructor (import del módulo), así
// que capturamos los handlers UNA vez aquí (no en beforeEach, que los limpiaría).
const requestHandler = requestUseMock.mock.calls[0]?.[0];
const responseErrorHandler = responseUseMock.mock.calls[0]?.[1];

beforeEach(async () => {
  vi.clearAllMocks();
  window.localStorage.clear();
  (isAuthDisabled as any).mockReturnValue(false);
});

describe("api client — request interceptor", () => {
  it("añade el header Authorization cuando hay un token válido", async () => {
    const token = "x".repeat(20);
    await secureStorage.set("access_token", token);

    const config: any = { headers: {} };
    const out = await requestHandler(config);

    expect(out.headers.Authorization).toBe(`Bearer ${token}`);
  });

  it("no añade Authorization cuando no hay token", async () => {
    const config: any = { headers: {} };
    const out = await requestHandler(config);
    expect(out.headers.Authorization).toBeUndefined();
  });
});

describe("api client — response error handler", () => {
  it("rechaza errores no-401 sin reintentar", async () => {
    // 400 (4xx no-reintentable) → rechaza directo. Nota: 5xx/429/red en
    // métodos idempotentes SÍ son reintentables (retry P6); por eso usamos 400.
    const err: any = { response: { status: 400 }, config: { headers: {} } };
    await expect(responseErrorHandler(err)).rejects.toBe(err);
  });

  it("reintenta la petición tras refrescar el token (401)", async () => {
    await secureStorage.set("refresh_token", "refresh-token");
    postMock.mockResolvedValue({
      data: { access_token: "new-at", refresh_token: "new-rt" },
    });
    const err: any = {
      response: { status: 401 },
      config: { headers: {}, _retry: false },
    };

    const result = await responseErrorHandler(err);

    expect(postMock).toHaveBeenCalled();
    expect(await secureStorage.get("access_token")).toBe("new-at");
    expect(result).toEqual({ data: "retried" });
  });

  it("rechaza un 401 cuando no hay refresh token", async () => {
    const err: any = {
      response: { status: 401 },
      config: { headers: {}, _retry: false },
    };
    await expect(responseErrorHandler(err)).rejects.toBe(err);
  });

  it("no reintenta cuando la autenticación está desactivada", async () => {
    (isAuthDisabled as any).mockReturnValue(true);
    const err: any = {
      response: { status: 401 },
      config: { headers: {}, _retry: false },
    };
    await expect(responseErrorHandler(err)).rejects.toBe(err);
    expect(postMock).not.toHaveBeenCalled();
  });
});

describe("api client — exports", () => {
  it("expone api (instancia axios) y apiClient", () => {
    expect(api).toBeDefined();
    expect(apiClient.axiosInstance).toBeDefined();
  });
});
