import { api } from "@/app/services/api/client";
import type { AxiosError } from "axios";

/**
 * app-update — lógica de comprobación de actualizaciones de la app móvil.
 *
 * Consulta el endpoint backend ``GET /api/v1/mobile/version`` y compara la
 * versión instalada (``NEXT_PUBLIC_APP_VERSION``) con la mínima y la última
 * disponibles. Devuelve un estado tipado que el hook/UI pueden consumir:
 *
 *   - ``required``   → la versión instalada es < ``min_version`` (bloqueante)
 *   - ``recommended``→ la versión instalada es < ``latest_version`` (aviso)
 *   - ``up-to-date`` → la versión instalada es >= ``latest_version``
 *   - ``unknown``    → no se pudo comprobar (falta config / sin red)
 */

export type UpdateStatus = "required" | "recommended" | "up-to-date" | "unknown";

export interface MobileVersionInfo {
  min_version: string;
  latest_version: string;
  update_url: string;
  status: UpdateStatus;
}

/**
 * Compara dos versiones semver "X.Y.Z" numéricamente. Devuelve:
 *   -1 si a < b, 0 si a == b, 1 si a > b.
 * Cualquier componente no numérico se trata como 0.
 */
export function compareVersions(a: string, b: string): number {
  const pa = a.split(".").map((n) => parseInt(n, 10) || 0);
  const pb = b.split(".").map((n) => parseInt(n, 10) || 0);
  const len = Math.max(pa.length, pb.length);
  for (let i = 0; i < len; i++) {
    const x = pa[i] ?? 0;
    const y = pb[i] ?? 0;
    if (x < y) return -1;
    if (x > y) return 1;
  }
  return 0;
}

/** Deriva el estado de actualización a partir de las versiones instaladas. */
export function resolveUpdateStatus(
  installed: string,
  minVersion: string,
  latestVersion: string
): UpdateStatus {
  if (compareVersions(installed, minVersion) < 0) return "required";
  if (compareVersions(installed, latestVersion) < 0) return "recommended";
  return "up-to-date";
}

/** Versión instalada de la app (inyectada en build). */
export function getInstalledVersion(): string {
  return process.env.NEXT_PUBLIC_APP_VERSION || "1.0.0";
}

/**
 * Consulta el backend y devuelve la info de versión con su estado derivado.
 * Ante cualquier error (red, 5xx, shape inesperado) devuelve ``unknown`` en
 * lugar de propagar la excepción, para que la UI nunca se rompa por esto.
 */
export async function fetchAppUpdate(): Promise<MobileVersionInfo> {
  try {
    const { data } = await api.get<MobileVersionInfo>("/mobile/version");
    const status = resolveUpdateStatus(
      getInstalledVersion(),
      data.min_version,
      data.latest_version
    );
    return { ...data, status };
  } catch (err) {
    // 404/500 o red caída → no molestar al usuario con un banner erróneo.
    const ax = err as AxiosError;
    if (ax.response?.status === 404) {
      return {
        min_version: getInstalledVersion(),
        latest_version: getInstalledVersion(),
        update_url: "",
        status: "unknown",
      };
    }
    return {
      min_version: "",
      latest_version: "",
      update_url: "",
      status: "unknown",
    };
  }
}
