/**
 * use-deep-links — utilidades para deep links en la app móvil.
 *
 * Soporta:
 *   - Esquema propietario: aibusiness://ruta/param
 *   - Universal links (https): https://aibusiness.app/ruta/param
 *   - Builder para generar deep links desde código.
 */

export interface DeepLinkData {
  path: string;
  params?: Record<string, string>;
}

export const SCHEME = "aibusiness";
export const WEB_HOST = "aibusiness.app";

const ROUTE_MAP: Record<string, string> = {
  vehicle: "/vehicle/",
  deal: "/deal/",
  search: "/search/",
};

/**
 * Parsea una URL (esquema propio o universal link) a un objeto `DeepLinkData`.
 * Devuelve `null` si el host/scheme no está autorizado.
 *
 * @example
 *   parseDeepLink("aibusiness://vehicle/123") // → { path: "vehicle/123" }
 *   parseDeepLink("https://aibusiness.app/vehicle/456") // → { path: "vehicle/456" }
 *   parseDeepLink("https://evil.com/hack") // → null
 */
export function parseDeepLink(url: string): DeepLinkData | null {
  try {
    const u = new URL(url);

    // Esquema propio: aibusiness://ruta/param
    if (u.protocol === `${SCHEME}:`) {
      return {
        path: (u.host + u.pathname).replace(/\/+$/, ""),
        params: Object.fromEntries(u.searchParams),
      };
    }

    // Universal link: https://aibusiness.app/ruta
    if (u.protocol === "https:" && u.hostname === WEB_HOST) {
      return {
        path: u.pathname.replace(/^\//, "").replace(/\/+$/, ""),
        params: Object.fromEntries(u.searchParams),
      };
    }

    return null;
  } catch {
    return null;
  }
}

/**
 * Resuelve un objeto `DeepLinkData` a una ruta de la app.
 *
 * @example
 *   resolveDeepLinkRoute({ path: "vehicle/123" }) // → "/vehicle/123"
 */
export function resolveDeepLinkRoute(data: DeepLinkData): string {
  const [entity, ...rest] = data.path.split("/");
  const id = rest.join("/");
  if (entity && id && ROUTE_MAP[entity]) {
    return `${ROUTE_MAP[entity]}${id}`;
  }
  return `/${data.path}`;
}

function toQuery(params?: Record<string, string>): string {
  if (!params || Object.keys(params).length === 0) return "";
  const qs = new URLSearchParams(params);
  return `?${qs.toString()}`;
}

/**
 * Builder para generar deep links desde código de forma tipada.
 *
 * @example
 *   deepLinkBuilder.vehicle("123") // → "aibusiness://vehicle/123"
 *   deepLinkBuilder.deal("456")    // → "aibusiness://deal/456"
 */
export const deepLinkBuilder = {
  vehicle: (id: string, params?: Record<string, string>): string =>
    `${SCHEME}://vehicle/${id}${toQuery(params)}`,

  deal: (id: string, params?: Record<string, string>): string =>
    `${SCHEME}://deal/${id}${toQuery(params)}`,

  search: (query: string, params?: Record<string, string>): string =>
    `${SCHEME}://search/${encodeURIComponent(query)}${toQuery(params)}`,
};