import { apiClient, api } from "@/app/services/api/client";

/**
 * Utility function to perform fetch requests with exponential backoff retries
 * for transient network errors, HTTP 429 (Rate Limit), and 5xx server errors.
 */
export async function fetchWithRetry(
  url: string,
  options: RequestInit = {},
  retries = 3,
  backoff = 1000
): Promise<Response> {
  try {
    const response = await fetch(url, options);

    if (response.status >= 500 || response.status === 429) {
      if (retries > 0) {
        await new Promise((resolve) => setTimeout(resolve, backoff));
        return fetchWithRetry(url, options, retries - 1, backoff * 2);
      }
    }

    return response;
  } catch (error) {
    if (retries > 0 && error instanceof TypeError) {
      await new Promise((resolve) => setTimeout(resolve, backoff));
      return fetchWithRetry(url, options, retries - 1, backoff * 2);
    }
    throw error;
  }
}

export { apiClient, api };
export default api;
