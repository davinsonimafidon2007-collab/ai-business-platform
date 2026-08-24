import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

// ---------------------------------------------------------------------------
// Mocks hoisteados
// ---------------------------------------------------------------------------
const mocks = vi.hoisted(() => ({
  mockCapacitor: {
    isNativePlatform: vi.fn(() => true),
    getPlatform: vi.fn(() => "android"),
  },
  mockApi: {
    post: vi.fn(async () => ({ data: {} })),
    get: vi.fn(),
  },
  mockPush: {
    requestPermissions: vi.fn(async () => ({ receive: "granted" })),
    register: vi.fn(async () => {}),
    addListener: vi.fn(async (_event: string, _cb: unknown) => ({
      remove: vi.fn(async () => {}),
    })),
  },
  mockLocalNotifications: {
    createChannel: vi.fn(async () => {}),
    schedule: vi.fn(async () => {}),
  },
}));

vi.mock("@capacitor/core", () => ({ Capacitor: mocks.mockCapacitor }));
vi.mock("@/app/services/api/client", () => ({ api: mocks.mockApi }));
vi.mock("@capacitor/push-notifications", () => ({
  PushNotifications: mocks.mockPush,
}));
vi.mock("@capacitor/local-notifications", () => ({
  LocalNotifications: mocks.mockLocalNotifications,
}));

import {
  initPushNotifications,
  unregisterPushNotifications,
  teardownPushNotifications,
} from "@/app/services/push-notifications";

type Handler = (payload: never) => void | Promise<void>;

/** Captura el callback registrado para un evento de PushNotifications. */
async function getHandler(event: string): Promise<Handler> {
  const calls = mocks.mockPush.addListener.mock.calls.filter(
    ([e]) => e === event
  );
  const last = calls[calls.length - 1];
  return last![1] as Handler;
}

/**
 * Estado nativo limpio antes de cada grupo. El propio teardown del servicio
 * resetea `initialized`, listeners y token — es justo lo que hace tras logout,
 * así que sirve de aislamiento entre tests sin recargar módulos.
 */
async function freshNativeState(): Promise<void> {
  await teardownPushNotifications();
  mocks.mockCapacitor.isNativePlatform.mockReturnValue(true);
  mocks.mockCapacitor.getPlatform.mockReturnValue("android");
  mocks.mockPush.requestPermissions.mockResolvedValue({ receive: "granted" });
}

let logSpy: ReturnType<typeof vi.spyOn>;
let errSpy: ReturnType<typeof vi.spyOn>;
let warnSpy: ReturnType<typeof vi.spyOn>;

describe("push-notifications (hardening #5)", () => {
  beforeEach(async () => {
    vi.clearAllMocks();
    logSpy = vi.spyOn(console, "log").mockImplementation(() => {});
    errSpy = vi.spyOn(console, "error").mockImplementation(() => {});
    warnSpy = vi.spyOn(console, "warn").mockImplementation(() => {});
    await freshNativeState();
  });

  afterEach(() => {
    logSpy.mockRestore();
    errSpy.mockRestore();
    warnSpy.mockRestore();
  });

  it("en web es no-op total (sin canal, sin listeners, sin register)", async () => {
    mocks.mockCapacitor.isNativePlatform.mockReturnValue(false);
    mocks.mockCapacitor.getPlatform.mockReturnValue("web");
    await initPushNotifications();
    expect(mocks.mockLocalNotifications.createChannel).not.toHaveBeenCalled();
    expect(mocks.mockPush.addListener).not.toHaveBeenCalled();
    expect(mocks.mockPush.register).not.toHaveBeenCalled();
  });

  it("permiso denegado → no registra ni llama a register()", async () => {
    mocks.mockPush.requestPermissions.mockResolvedValue({
      receive: "denied",
    });
    await initPushNotifications();
    expect(mocks.mockPush.addListener).not.toHaveBeenCalled();
    expect(mocks.mockPush.register).not.toHaveBeenCalled();
  });

  it("flujo nativo: crea canal, registra 4 listeners y llama register()", async () => {
    await initPushNotifications();
    expect(errSpy).not.toHaveBeenCalled();
    expect(mocks.mockLocalNotifications.createChannel).toHaveBeenCalledWith(
      expect.objectContaining({ id: "aibusiness_default" })
    );
    const events = mocks.mockPush.addListener.mock.calls.map(([e]) => e);
    expect(events).toEqual([
      "registration",
      "registrationError",
      "pushNotificationReceived",
      "pushNotificationActionPerformed",
    ]);
    expect(mocks.mockPush.register).toHaveBeenCalledTimes(1);
  });

  it("MOBILE-HARDENING #5: el valor del token FCM nunca aparece en logs", async () => {
    await initPushNotifications();

    const handler = await getHandler("registration");
    const secret = "fcm-token-SUPER-secreto-abc123";
    await (handler as (t: { value: string }) => Promise<void>)({
      value: secret,
    });

    const allOutput = [
      ...logSpy.mock.calls.flat(),
      ...errSpy.mock.calls.flat(),
      ...warnSpy.mock.calls.flat(),
    ].join("\n");
    expect(allOutput).not.toContain(secret);
    // El token SÍ se envía al backend.
    expect(mocks.mockApi.post).toHaveBeenCalledWith("/notifications/register", {
      token: secret,
      platform: "android",
    });
  });

  it("segunda llamada es idempotente (guard initialized)", async () => {
    await initPushNotifications();
    const callsAfterFirst = mocks.mockPush.addListener.mock.calls.length;
    expect(callsAfterFirst).toBe(4);
    await initPushNotifications();
    expect(mocks.mockPush.addListener.mock.calls.length).toBe(callsAfterFirst);
  });

  it("MOBILE-HARDENING #5: IDs de notificación normalizados a int32 válido", async () => {
    await initPushNotifications();
    const received = await getHandler("pushNotificationReceived");

    for (const rawId of ["99999999999999", "no-es-numero", undefined]) {
      await (
        received as (
          n: { title?: string; body?: string; id?: string }
        ) => Promise<void>
      )({
        title: "Alerta",
        body: "Nueva oportunidad",
        id: rawId as string | undefined,
      });
    }

    const calls = mocks.mockLocalNotifications.schedule.mock
      .calls as unknown as Array<Array<{ notifications: Array<{ id: number }> }>>;
    expect(calls).toHaveLength(3);
    for (const call of calls) {
      const payload = call[0];
      const id = payload.notifications[0].id;
      expect(Number.isInteger(id)).toBe(true);
      expect(id).toBeGreaterThanOrEqual(0);
      expect(id).toBeLessThanOrEqual(2147483647);
    }
  });

  it("el payload completo no se vuelca a logs (solo el título)", async () => {
    await initPushNotifications();
    const received = await getHandler("pushNotificationReceived");
    await (
      received as (n: { title?: string; body?: string }) => Promise<void>
    )({
      title: "Oferta",
      body: "Datos sensibles del payload interno XYZ",
    });
    const output = [...logSpy.mock.calls.flat(), ...errSpy.mock.calls.flat()].join(
      "\n"
    );
    expect(output).not.toContain("Datos sensibles del payload interno XYZ");
    expect(output).toContain("Oferta");
  });

  describe("tap routing (deepLink:navigate)", () => {
    let dispatched: Array<CustomEvent<{ url: string }>> = [];
    let capture: (evt: Event) => void;

    beforeEach(() => {
      dispatched = [];
      capture = (evt: Event) =>
        dispatched.push(evt as CustomEvent<{ url: string }>);
      window.addEventListener("deepLink:navigate", capture);
    });

    afterEach(() => {
      window.removeEventListener("deepLink:navigate", capture);
    });

    it("data.deepLink dispara evento de navegación", async () => {
      await initPushNotifications();
      const action = await getHandler("pushNotificationActionPerformed");
      action({
        notification: { data: { deepLink: "aibusiness://vehicle/123" } },
      } as never);
      expect(dispatched).toHaveLength(1);
      expect(dispatched[0].detail.url).toBe("aibusiness://vehicle/123");
    });

    it("type=opportunity construye deep link con opportunityId", async () => {
      await initPushNotifications();
      const action = await getHandler("pushNotificationActionPerformed");
      action({
        notification: { data: { type: "opportunity", opportunityId: 55 } },
      } as never);
      expect(dispatched[0].detail.url).toBe("aibusiness://opportunity/55");
    });

    it("type=deal construye deep link con dealId", async () => {
      await initPushNotifications();
      const action = await getHandler("pushNotificationActionPerformed");
      action({
        notification: { data: { type: "deal", dealId: 77 } },
      } as never);
      expect(dispatched[0].detail.url).toBe("aibusiness://deal/77");
    });

    it("sin datos navegables no despacha nada", async () => {
      await initPushNotifications();
      const action = await getHandler("pushNotificationActionPerformed");
      action({ notification: { data: { foo: "bar" } } } as never);
      action({ notification: {} } as never);
      expect(dispatched).toHaveLength(0);
    });
  });

  describe("unregister y teardown", () => {
    it("unregister en web es no-op", async () => {
      mocks.mockCapacitor.getPlatform.mockReturnValue("web");
      await unregisterPushNotifications();
      expect(mocks.mockApi.post).not.toHaveBeenCalled();
    });

    it("unregister sin token previo es no-op", async () => {
      await unregisterPushNotifications();
      expect(mocks.mockApi.post).not.toHaveBeenCalled();
    });

    it("teardown remueve todos los listeners y permite re-inicializar", async () => {
      const removeSpies: Array<ReturnType<typeof vi.fn>> = [];
      mocks.mockPush.addListener.mockImplementation(async () => {
        const remove = vi.fn(async () => {});
        removeSpies.push(remove);
        return { remove };
      });

      await initPushNotifications();
      expect(mocks.mockPush.addListener).toHaveBeenCalledTimes(4);

      const registration = await getHandler("registration");
      await (registration as (t: { value: string }) => Promise<void>)({
        value: "tok",
      });

      await teardownPushNotifications();
      expect(removeSpies).toHaveLength(4);
      for (const spy of removeSpies) expect(spy).toHaveBeenCalled();
      expect(mocks.mockApi.post).toHaveBeenCalledWith(
        "/notifications/unregister",
        { token: "tok" }
      );

      // Re-login: init vuelve a registrar los 4 listeners desde cero.
      await initPushNotifications();
      expect(mocks.mockPush.addListener).toHaveBeenCalledTimes(8);
      const events = mocks.mockPush.addListener.mock.calls
        .slice(4)
        .map(([e]) => e);
      expect(events).toEqual([
        "registration",
        "registrationError",
        "pushNotificationReceived",
        "pushNotificationActionPerformed",
      ]);
    });
  });
});
