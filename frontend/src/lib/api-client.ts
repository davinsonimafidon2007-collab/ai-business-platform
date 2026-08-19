import { apiClient, api } from "@/app/services/api/client";

/**
 * Realiza peticiones fetch con reintentos y retroceso exponencial (exponential backoff)
 * ante errores transitorios de red o códigos HTTP 429 / 5xx.
 */
export async function fetchWithRetry(
  url: string,
  options: RequestInit = {},
  retries = 3,
  backoff = 1000
): Promise<Response> {
  try {
    const response = await fetch(url, options);

    // Si es un error de servidor (5xx) o Too Many Requests (429), reintentar
    if (response.status >= 500 || response.status === 429) {
      if (retries > 0) {
        await new Promise((resolve) => setTimeout(resolve, backoff));
        return fetchWithRetry(url, options, retries - 1, backoff * 2);
      }
    }

    return response;
  } catch (error) {
    // Errores de red (offline, DNS, etc.)
    if (retries > 0 && (error instanceof TypeError || error instanceof Error)) {
      await new Promise((resolve) => setTimeout(resolve, backoff));
      return fetchWithRetry(url, options, retries - 1, backoff * 2);
    }
    throw error;
  }
}

export { apiClient, api };
export default api;
