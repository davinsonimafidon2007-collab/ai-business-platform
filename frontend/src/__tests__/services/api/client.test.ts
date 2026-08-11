import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

// Mock de axios: create() devuelve una instancia invocable con interceptores.
// El error handler se registra como 2º arg de response.interceptors.use.
const { mockInstance, mockCreate, requestHandler, responseHandler } = vi.hoisted(() => {
  const requestHandler = vi.fn();
  const responseHandler = vi.fn();
  const mockInstance = Object.assign(vi.fn(), {
    interceptors: {
      request: { use: requestHandler },
      response: { use: responseHandler },
    },
  });
  return {
    mockInstance,
    mockCreate: vi.fn(() => mockInstance),
    requestHandler,
    responseHandler,
  };
});

vi.mock("axios", () => ({
  default: { create: mockCreate },
}));

// Modo personal: sin sesión que refrescar (evita el loop 401 en estos tests).
process.env.NEXT_PUBLIC_AUTH_DISABLED = "true";

import { apiClient } from "@/app/services/api/client";

// Capturado una vez a nivel de módulo: el interceptor se registra al construir
// el ApiClient (import). Un clearAllMocks en beforeEach lo borraría.
const errorHandler = responseHandler.mock.calls[0][1];

interface FakeAxiosError {
  config: {
    method: string;
    headers: Record<string, string>;
    url: string;
    _retryCount?: number;
    _retry?: boolean;
  };
  response?: { status: number; data: null; headers: Record<string, string> };
}

function makeError(method: string, status?: number): FakeAxiosError {
  const err: FakeAxiosError = {
    config: { method, headers: {}, url: "/x" },
  };
  if (status !== undefined) {
    err.response = { status, data: null, headers: {} };
  }
  return err;
}

describe("api client retry with backoff (P6)", () => {
  beforeEach(() => {
    mockInstance.mockReset();
    vi.spyOn(Math, "random").mockReturnValue(0); // delays 0 → tests rápidos
  });

  afterEach(() => {
    vi.restoreAllMocks();
    delete process.env.NEXT_PUBLIC_AUTH_DISABLED;
  });

  it("retries network errors up to max attempts and then rejects", async () => {
    // Simula la cadena real de axios: un reintento fallido vuelve a pasar por
    // el error handler (reintenta hasta agotar RETRY_MAX_ATTEMPTS).
    const seenRetryCounts: (number | undefined)[] = [];
    mockInstance.mockImplementation((config: FakeAxiosError["config"]) => {
      seenRetryCounts.push(config._retryCount);
      const err = makeError("get");
      err.config = config; // conserva _retryCount que el handler ya marcó
      return errorHandler(err);
    });

    await expect(errorHandler(makeError("get"))).rejects.toBeDefined();

    expect(mockInstance).toHaveBeenCalledTimes(2); // 2 reintentos
    expect(seenRetryCounts).toEqual([1, 2]);
  });

  it("retries 503 then succeeds on the first retry", async () => {
    mockInstance.mockResolvedValueOnce({ data: { ok: true } });

    const result = await errorHandler(makeError("get", 503));

    expect(result).toEqual({ data: { ok: true } });
    expect(mockInstance).toHaveBeenCalledTimes(1);
  });

  it("does not retry 4xx errors other than 429", async () => {
    mockInstance.mockRejectedValue(makeError("get"));

    await expect(errorHandler(makeError("get", 403))).rejects.toBeDefined();

    expect(mockInstance).not.toHaveBeenCalled();
  });

  it("does not retry non-idempotent methods", async () => {
    mockInstance.mockRejectedValue(makeError("post"));

    await expect(errorHandler(makeError("post", 503))).rejects.toBeDefined();

    expect(mockInstance).not.toHaveBeenCalled();
  });

  it("does not retry 401 (goes to the refresh flow instead)", async () => {
    mockInstance.mockRejectedValue(makeError("get"));

    await expect(errorHandler(makeError("get", 401))).rejects.toBeDefined();

    expect(mockInstance).not.toHaveBeenCalled();
  });

  it("exposes the axios instance to services", () => {
    expect(apiClient.axiosInstance).toBe(mockInstance);
  });
});
