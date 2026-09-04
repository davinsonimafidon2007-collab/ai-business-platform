import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";

// ---------------------------------------------------------------------------
// Mocks hoisteados
// ---------------------------------------------------------------------------
const mocks = vi.hoisted(() => ({
  mockCapacitor: {
    isNativePlatform: vi.fn(() => false),
    getPlatform: vi.fn(() => "web"),
  },
  mockRouter: {
    push: vi.fn(),
    replace: vi.fn(),
    back: vi.fn(),
  },
  mockApp: {
    addListener: vi.fn(),
    getLaunchUrl: vi.fn<() => Promise<{ url: string | null }>>(),
  },
}));

vi.mock("@capacitor/core", () => ({ Capacitor: mocks.mockCapacitor }));
vi.mock("@capacitor/app", () => ({ App: mocks.mockApp }));
vi.mock("next/navigation", () => ({ useRouter: () => mocks.mockRouter }));

import {
  parseDeepLink,
  resolveDeepLinkRoute,
  deepLinkBuilder,
  SCHEME,
  WEB_HOST,
  useDeepLinks,
} from "@/app/hooks/use-deep-links";

describe("parseDeepLink — custom scheme", () => {
  it("aibusiness://vehicle/123", () => {
    const d = parseDeepLink("aibusiness://vehicle/123");
    expect(d).not.toBeNull();
    expect(d!.path).toBe("vehicle/123");
  });

  it("aibusiness://search?q=Toyota extrae queryParams", () => {
    const d = parseDeepLink("aibusiness://search?q=Toyota");
    expect(d).not.toBeNull();
    expect(d!.path).toBe("search");
    expect(d!.queryParams).toEqual({ q: "Toyota" });
  });
});

describe("parseDeepLink — App Links (https)", () => {
  it("https://aibusiness.app/vehicle/123", () => {
    const d = parseDeepLink("https://aibusiness.app/vehicle/123");
    expect(d).not.toBeNull();
    expect(d!.path).toBe("vehicle/123");
  });

  it("https://app.aibusiness.com/deal/123", () => {
    // Host legado: sigue parseándose por compatibilidad de enlaces ya
    // emitidos, aunque el manifest ya no lo declara como App Link productivo.
    const d = parseDeepLink("https://app.aibusiness.com/deal/123");
    expect(d).not.toBeNull();
    expect(d!.path).toBe("deal/123");
  });
});

describe("parseDeepLink — URLs inválidas", () => {
  it.each([
    ["https://evil.example.com/phishing", "host ajeno"],
    ["notaurl", "string sin formato URL"],
    ["", "vacío"],
  ])("%s (%s) → null", (input) => {
    expect(parseDeepLink(input)).toBeNull();
  });
});

describe("resolveDeepLinkRoute — rutas", () => {
  // Regresión: /vehicle/{id} y /deal/{id} (singular) nunca han existido
  // como rutas en el frontend (ni /vehicles ni /deals tienen sub-ruta
  // [id] — el detalle de vehículo es un drawer con estado local, no una
  // URL). Antes del fix, tocar uno de estos deep links producía un 404
  // real dentro de la app nativa. Aterrizan en el listado real hasta que
  // exista una ruta de detalle direccionable.
  it("vehicle/:id → listado (no existe ruta de detalle direccionable)", () => {
    expect(resolveDeepLinkRoute({ path: "vehicle/123" })).toBe("/vehicles");
  });

  it("deal/:id → listado (no existe ruta de detalle direccionable)", () => {
    expect(resolveDeepLinkRoute({ path: "deal/123" })).toBe("/deals");
  });

  // Regresión: antes resolvía a "/opportunities?id=123" — esa ruta SÍ
  // existe pero es el LISTADO, que nunca lee el query param "id". Tocar
  // una notificación push de una oportunidad (ver push-notifications.ts,
  // caso "opportunity") llevaba al usuario a la lista completa en vez de
  // a la oportunidad concreta que necesitaba su aprobación.
  // /opportunities/{id} SÍ existe y es la página de detalle real (ver
  // OpportunityCard.tsx, que enlaza exactamente a esa ruta).
  it("opportunity/:id → página de detalle real", () => {
    expect(resolveDeepLinkRoute({ path: "opportunity/123" })).toBe(
      "/opportunities/123"
    );
  });

  it("MOBILE-HARDENING #4: búsqueda en el PATH del builder se resuelve como query", () => {
    // Antes: builder.search colocaban la búsqueda en el path pero el resolver
    // solo leía queryParams → la búsqueda se perdía silenciosamente.
    const built = deepLinkBuilder.search("Toyota");
    expect(built).toBe("aibusiness://search/Toyota");
    const route = resolveDeepLinkRoute(parseDeepLink(built)!);
    expect(route).toBe("/search?q=Toyota");
  });

  it("búsqueda con queryParams explícitos se respeta", () => {
    const route = resolveDeepLinkRoute(
      parseDeepLink("aibusiness://search?q=Honda&year=2020")!
    );
    expect(route).toContain("q=Honda");
    expect(route).toContain("year=2020");
  });

  it("path vacío → dashboard", () => {
    expect(resolveDeepLinkRoute({ path: "" })).toBe("/dashboard");
  });

  it("recurso desconocido → null", () => {
    expect(resolveDeepLinkRoute({ path: "unknown/1" })).toBeNull();
  });
});

describe("deepLinkBuilder — round trip", () => {
  it("vehicle/deal/opportunity/settings/dashboard producen links parseables", () => {
    expect(deepLinkBuilder.vehicle("9")).toBe("aibusiness://vehicle/9");
    expect(deepLinkBuilder.deal("7")).toBe("aibusiness://deal/7");
    expect(deepLinkBuilder.opportunity("5")).toBe("aibusiness://opportunity/5");
    expect(deepLinkBuilder.settings()).toBe("aibusiness://settings");
    expect(deepLinkBuilder.dashboard()).toBe("aibusiness://dashboard");

    for (const url of [
      deepLinkBuilder.vehicle("9"),
      deepLinkBuilder.deal("7"),
      deepLinkBuilder.opportunity("5"),
    ]) {
      expect(resolveDeepLinkRoute(parseDeepLink(url)!)).not.toBeNull();
    }
  });
});

describe("useDeepLinks — ciclo de vida nativo", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.mockCapacitor.isNativePlatform.mockReturnValue(true);
    mocks.mockApp.addListener.mockResolvedValue({ remove: vi.fn() });
    mocks.mockApp.getLaunchUrl.mockResolvedValue({ url: null });
  });

  it("web no registra listeners", async () => {
    mocks.mockCapacitor.isNativePlatform.mockReturnValue(false);
    renderHook(() => useDeepLinks());
    await waitFor(() => expect(mocks.mockApp.addListener).not.toHaveBeenCalled());
  });

  it("COLD START: navega a la URL de lanzamiento pendiente", async () => {
    mocks.mockApp.getLaunchUrl.mockResolvedValue({
      url: "aibusiness://vehicle/42",
    });
    renderHook(() => useDeepLinks());
    await waitFor(() =>
      expect(mocks.mockRouter.push).toHaveBeenCalledWith("/vehicles")
    );
  });

  it("appUrlOpen posterior navega al recurso", async () => {
    let handler: ((d: { url: string }) => void) | null = null;
    mocks.mockApp.addListener.mockImplementation(async (_evt, cb) => {
      handler = cb;
      return { remove: vi.fn() };
    });
    renderHook(() => useDeepLinks());
    await waitFor(() => expect(handler).not.toBeNull());
    handler!({ url: "aibusiness://deal/77" });
    await waitFor(() =>
      expect(mocks.mockRouter.push).toHaveBeenCalledWith("/deals")
    );
  });

  it("COLD START: notificación push de oportunidad abre el detalle real, no el listado", async () => {
    // Regresión del flujo real push-notifications.ts (case "opportunity")
    // -> deepLinkBuilder.opportunity -> useDeepLinks. Antes del fix
    // terminaba en "/opportunities?id=456" (el listado).
    mocks.mockApp.getLaunchUrl.mockResolvedValue({
      url: "aibusiness://opportunity/456",
    });
    renderHook(() => useDeepLinks());
    await waitFor(() =>
      expect(mocks.mockRouter.push).toHaveBeenCalledWith("/opportunities/456")
    );
  });

  it("cleanup: desmontar remueve el listener registrado", async () => {
    const removeSpy = vi.fn(async () => {});
    mocks.mockApp.addListener.mockResolvedValue({ remove: removeSpy });
    const { unmount } = renderHook(() => useDeepLinks());
    await waitFor(() => expect(mocks.mockApp.addListener).toHaveBeenCalled());
    unmount();
    expect(removeSpy).toHaveBeenCalled();
  });

  // MO-M-006: regresión del flujo real de push-notifications.ts, caso
  // "opportunity" — despacha `new CustomEvent("deepLink:navigate", {detail:
  // {url}})` en vez de pasar por App.addListener("appUrlOpen", ...). Antes
  // de este fix nada escuchaba ese evento: tocar una notificación push de
  // una oportunidad pendiente de aprobación no navegaba a ningún sitio.
  it("deepLink:navigate (CustomEvent de push-notifications.ts) navega al detalle real", async () => {
    renderHook(() => useDeepLinks());
    await waitFor(() => expect(mocks.mockApp.addListener).toHaveBeenCalled());

    window.dispatchEvent(
      new CustomEvent("deepLink:navigate", {
        detail: { url: "aibusiness://opportunity/999" },
      })
    );

    await waitFor(() =>
      expect(mocks.mockRouter.push).toHaveBeenCalledWith("/opportunities/999")
    );
  });

  it("deepLink:navigate también funciona en web (fuera de plataforma nativa)", async () => {
    mocks.mockCapacitor.isNativePlatform.mockReturnValue(false);
    renderHook(() => useDeepLinks());

    window.dispatchEvent(
      new CustomEvent("deepLink:navigate", {
        detail: { url: "aibusiness://opportunity/111" },
      })
    );

    await waitFor(() =>
      expect(mocks.mockRouter.push).toHaveBeenCalledWith("/opportunities/111")
    );
  });
});

describe("constantes públicas", () => {
  it("scheme y host web documentados", () => {
    expect(SCHEME).toBe("aibusiness");
    expect(WEB_HOST).toBe("aibusiness.app");
  });
});
